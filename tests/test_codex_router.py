"""The Codex account is CHOSEN BY THE ROUTER, and never guessed.

`resolve_codex_home` used to refuse whenever no flag and no env var named a
home, so the operator picked by hand. Hand-picking is how a run lands on an
exhausted account: headroom moves hour by hour and the operator is working from
memory. `quotapick` reads live per-account usage, so from 2026-09-15 the
resolver asks it.

The refusal did not go away, it moved. These tests pin the line between the two:
the router ANSWERING is not the same as the router answering with an account
that can actually be spent, and everything below is about that distinction.

Offline by construction. Every test injects a fake router; none shells out.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit import accounts  # noqa: E402
from packages.llmkit.accounts import (AccountNotChosen,  # noqa: E402
                                      RouterUnavailable, ROUTER_CONTRACT_VERSION,
                                      resolve_codex_home, router_codex_accounts,
                                      router_pick_codex_home)

#: A real `quotapick pick --only codex --dry-run --json` body, captured
#: 2026-09-15 at a moment when every Codex account was out of quota. It is kept
#: verbatim because the thing it proves is a claim about the router's real
#: behaviour, and a hand-written dict would prove only that the test author
#: believed it.
EXHAUSTED = json.loads(
    (REPO / "tests/fixtures/quotapick_pick_all_exhausted.json").read_text())


def _status(*ids: str, provider: str = "codex") -> dict:
    return {"contract_version": ROUTER_CONTRACT_VERSION,
            "accounts": [{"id": i, "provider": provider} for i in ids]}


def _pick(account: str, home: str, *, fits: bool = True,
          meets_policy: bool = True, provider: str = "codex") -> dict:
    return {"contract_version": ROUTER_CONTRACT_VERSION,
            "decision": {"account": account, "provider": provider, "fits": fits,
                         "meets_policy": meets_policy, "reason": "test"},
            "exec": {"env": {"CODEX_HOME": home}}}


def _route(monkeypatch, status: dict, pick: dict | None = None) -> list[list[str]]:
    """Answer both router calls from canned bodies; record the argv of each."""
    seen: list[list[str]] = []

    def fake(args, *, timeout=None):
        seen.append(list(args))
        return status if args[0] == "status" else pick
    monkeypatch.setattr(accounts, "_router_json", fake)
    return seen


@pytest.fixture(autouse=True)
def _no_inherited_choice(monkeypatch):
    monkeypatch.delenv("CELEB_CODEX_HOME", raising=False)


# --------------------------------------------------------------------------
# The happy path, and the two overrides that must still outrank the router.
# --------------------------------------------------------------------------

def test_with_nothing_named_the_router_chooses(monkeypatch):
    _route(monkeypatch, _status("codex", "codex_b"),
           _pick("codex_b", "/tmp/.codex-b"))
    assert resolve_codex_home(None) == "/tmp/.codex-b"


def test_an_explicit_home_and_the_env_var_both_outrank_the_router(monkeypatch):
    def explode(*a, **k):
        pytest.fail("the router was consulted although a home was named")
    monkeypatch.setattr(accounts, "_router_json", explode)
    assert resolve_codex_home("/tmp/.codex-z") == "/tmp/.codex-z"
    monkeypatch.setenv("CELEB_CODEX_HOME", "/tmp/.codex-y")
    assert resolve_codex_home(None) == "/tmp/.codex-y"


def test_the_chosen_account_is_announced(monkeypatch, capsys):
    """A router picking silently is an inherited CODEX_HOME with extra steps."""
    _route(monkeypatch, _status("codex", "codex_b"),
           _pick("codex_b", "/tmp/.codex-b"))
    resolve_codex_home(None)
    err = capsys.readouterr().err
    assert "codex_b" in err and "/tmp/.codex-b" in err


# --------------------------------------------------------------------------
# A RETURNED ACCOUNT IS NOT AN AVAILABLE ONE. This is the load-bearing guard.
# --------------------------------------------------------------------------

def test_an_account_the_router_says_does_not_fit_is_refused(monkeypatch):
    """Measured: asked to choose among accounts that were ALL out of quota, the
    router exits 0 and returns `"account": "codex"` with `fits: false`. Reading
    the account and skipping the flag routes the whole run onto a 0.0% account,
    which fails as `auth_or_quota` and reads like a broken judge."""
    assert EXHAUSTED["decision"]["account"], "fixture no longer names an account"
    assert EXHAUSTED["decision"]["fits"] is False, "fixture no longer exhausted"
    _route(monkeypatch, _status("codex", "codex_b"), EXHAUSTED)
    with pytest.raises(RouterUnavailable) as e:
        resolve_codex_home(None)
    assert "out of quota" in str(e.value), "the refusal must quote the reason"


def test_meets_policy_false_is_refused_even_when_it_fits(monkeypatch):
    _route(monkeypatch, _status("codex"),
           _pick("codex", "/tmp/.codex", meets_policy=False))
    with pytest.raises(RouterUnavailable):
        resolve_codex_home(None)


def test_no_account_at_all_is_refused(monkeypatch):
    nothing = {"contract_version": ROUTER_CONTRACT_VERSION,
               "decision": {"account": None, "fits": False,
                            "meets_policy": False, "reason": "none visible"},
               "exec": {"env": {}}}
    _route(monkeypatch, _status("codex"), nothing)
    with pytest.raises(RouterUnavailable):
        resolve_codex_home(None)


def test_a_non_codex_provider_is_refused(monkeypatch):
    """CODEX_HOME pointed at a Claude config dir would not fail loudly; it would
    start a Codex judge on a directory holding no Codex credentials."""
    _route(monkeypatch, _status("codex"),
           _pick("claude_d", "/tmp/.claude-d", provider="claude"))
    with pytest.raises(RouterUnavailable) as e:
        resolve_codex_home(None)
    assert "provider" in str(e.value)


def test_a_decision_without_a_codex_home_is_refused(monkeypatch):
    blank = _pick("codex_b", "")
    _route(monkeypatch, _status("codex_b"), blank)
    with pytest.raises(RouterUnavailable):
        resolve_codex_home(None)


# --------------------------------------------------------------------------
# The candidate list is derived, not written down.
# --------------------------------------------------------------------------

def test_the_candidates_are_derived_from_the_router_not_hardcoded(monkeypatch):
    """`--only codex,codex_b` is right today and wrong the day a third Codex
    account appears. The ids come from `status`, filtered on provider."""
    seen = _route(monkeypatch, _status("codex", "codex_b", "codex_c"),
                  _pick("codex_c", "/tmp/.codex-c"))
    assert resolve_codex_home(None) == "/tmp/.codex-c"
    pick_argv = [a for a in seen if a[0] == "pick"][0]
    assert "codex,codex_b,codex_c" in pick_argv


def test_claude_accounts_are_never_offered_as_candidates(monkeypatch):
    status = {"contract_version": ROUTER_CONTRACT_VERSION, "accounts": [
        {"id": "claude_d", "provider": "claude"},
        {"id": "codex_b", "provider": "codex"}]}
    seen = _route(monkeypatch, status, _pick("codex_b", "/tmp/.codex-b"))
    resolve_codex_home(None)
    pick_argv = [a for a in seen if a[0] == "pick"][0]
    assert "codex_b" in pick_argv and "claude_d" not in ",".join(pick_argv)


def test_a_router_that_knows_no_codex_account_is_refused(monkeypatch):
    monkeypatch.setattr(accounts, "_router_json",
                        lambda a, timeout=None: _status())
    with pytest.raises(RouterUnavailable):
        router_codex_accounts()


def test_no_codex_account_id_is_written_into_the_module():
    """The same bug as a hardcoded config dir, one step removed."""
    src = (REPO / "packages/llmkit/accounts.py").read_text()
    code = "\n".join(l for l in src.splitlines()
                     if not l.lstrip().startswith("#"))
    assert '"codex_b"' not in code and "'codex_b'" not in code


# --------------------------------------------------------------------------
# The transport. The exit code proves nothing; only the body does.
# --------------------------------------------------------------------------

def _fake_proc(stdout: str, rc: int = 0):
    return subprocess.CompletedProcess([], rc, stdout=stdout, stderr="")


def test_a_missing_router_refuses_and_names_the_override(monkeypatch):
    monkeypatch.setattr(accounts.shutil, "which", lambda _: None)
    with pytest.raises(RouterUnavailable) as e:
        resolve_codex_home(None)
    assert "CELEB_CODEX_HOME" in str(e.value)


def test_an_unknown_contract_version_refuses_rather_than_guessing(monkeypatch):
    """The router ships from its own repo on its own release cycle. A parser
    that reads an unknown shape finds no `fits` key and would refuse anyway, or
    worse finds a key that has been repurposed."""
    monkeypatch.setattr(accounts.shutil, "which", lambda _: "/usr/bin/quotapick")
    monkeypatch.setattr(accounts.subprocess, "run",
                        lambda *a, **k: _fake_proc(json.dumps(
                            {"contract_version": ROUTER_CONTRACT_VERSION + 99})))
    with pytest.raises(RouterUnavailable) as e:
        resolve_codex_home(None)
    assert "contract_version" in str(e.value)


def test_output_that_is_not_json_refuses_even_on_exit_zero(monkeypatch):
    monkeypatch.setattr(accounts.shutil, "which", lambda _: "/usr/bin/quotapick")
    monkeypatch.setattr(accounts.subprocess, "run",
                        lambda *a, **k: _fake_proc("not json at all", rc=0))
    with pytest.raises(RouterUnavailable):
        resolve_codex_home(None)


def test_a_hung_router_refuses_rather_than_blocking_forever(monkeypatch):
    monkeypatch.setattr(accounts.shutil, "which", lambda _: "/usr/bin/quotapick")

    def hang(*a, **k):
        raise subprocess.TimeoutExpired(cmd="quotapick", timeout=30)
    monkeypatch.setattr(accounts.subprocess, "run", hang)
    with pytest.raises(RouterUnavailable) as e:
        resolve_codex_home(None)
    assert "CELEB_CODEX_HOME" in str(e.value)


def test_the_router_is_asked_for_a_dry_run(monkeypatch):
    """`pick` without --dry-run writes router state and can spawn. This only
    wants the decision."""
    seen = _route(monkeypatch, _status("codex_b"), _pick("codex_b", "/tmp/.codex-b"))
    resolve_codex_home(None)
    pick_argv = [a for a in seen if a[0] == "pick"][0]
    assert "--dry-run" in pick_argv and "--json" in pick_argv


# --------------------------------------------------------------------------
# Callers catching the old exception must still catch this one.
# --------------------------------------------------------------------------

def test_a_router_refusal_is_still_an_account_not_chosen(monkeypatch):
    _route(monkeypatch, _status("codex"), EXHAUSTED)
    with pytest.raises(AccountNotChosen):
        resolve_codex_home(None)


def test_the_refusal_lists_the_homes_on_this_machine(monkeypatch, tmp_path):
    (tmp_path / ".codex-q").mkdir()
    (tmp_path / ".codex-q" / "auth.json").write_text("{}")
    _route(monkeypatch, _status("codex"), EXHAUSTED)
    with pytest.raises(RouterUnavailable) as e:
        resolve_codex_home(None, home=tmp_path)
    assert ".codex-q" in str(e.value), "the override offer needs the homes"
