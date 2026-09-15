"""The Codex judge runs under an account that was CHOSEN, not inherited.

`CodexJudge` passed no environment to its subprocess at all -- plain
`subprocess.run(cmd, cwd=jail)` -- so every call inherited the shell's
CODEX_HOME, which is normally unset and resolves to `~/.codex`. Measured
2026-09-15: a second Codex account with a FULL weekly window sat unreachable
while runs failed on the exhausted one, and no flag could redirect them.

The `cdx` router picks the right account (`cdx -> codex_b`, verified). This
class was simply invoking `codex` underneath it, which the router never sees.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.accounts import (AccountNotChosen,  # noqa: E402
                                      discover_codex_homes, resolve_codex_home)
from packages.llmkit.judges import CodexJudge  # noqa: E402


def test_the_judge_sets_codex_home_in_the_child_environment():
    j = CodexJudge("astra", "gpt-6-astra", config_dir="/tmp/.codex-z")
    assert j._env()["CODEX_HOME"] == "/tmp/.codex-z"


def test_the_child_never_inherits_an_api_key(monkeypatch):
    """The subscription-only assertion used to read THIS process's environment
    while the child got a different one. Both are stripped from what the child
    actually sees."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-should-not-reach-the-child")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-nor-this")
    env = CodexJudge("astra", "gpt-6-astra", config_dir="/tmp/.codex-z")._env()
    assert "OPENAI_API_KEY" not in env and "ANTHROPIC_API_KEY" not in env


def test_the_subprocess_is_given_that_environment():
    """A _env() that nothing passes to subprocess.run is decoration.

    Asserted on the source because running it would spend quota. The call used
    to be `subprocess.run(cmd, cwd=jail, capture_output=True, ...)` with no
    `env=`, which is exactly the bug.
    """
    src = (REPO / "packages/llmkit/judges.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.ClassDef) and node.name == "CodexJudge"):
            continue
        calls = [n for n in ast.walk(node)
                 if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == "run"]
        assert calls, "CodexJudge no longer runs a subprocess"
        for c in calls:
            assert any(kw.arg == "env" for kw in c.keywords), (
                "CodexJudge runs a subprocess without env=, so it inherits the "
                "shell's CODEX_HOME and the account choice is hidden")
        return
    pytest.fail("CodexJudge not found")


def test_homes_are_discovered_by_globbing_not_listed():
    homes = discover_codex_homes()
    assert homes, "no Codex homes found on this machine"
    # A letter-by-letter list is the same bug one step removed; the account
    # count changes and has changed.
    src = (REPO / "packages/llmkit/accounts.py").read_text()
    assert '.codex-*' in src


def test_there_is_no_default_codex_account(monkeypatch):
    monkeypatch.delenv("CELEB_CODEX_HOME", raising=False)
    with pytest.raises(AccountNotChosen) as e:
        resolve_codex_home(None)
    assert "hidden" in str(e.value), "the refusal must say WHY there is no default"


def test_an_explicit_home_and_the_env_var_both_work(monkeypatch):
    monkeypatch.delenv("CELEB_CODEX_HOME", raising=False)
    assert resolve_codex_home("/tmp/.codex-z") == "/tmp/.codex-z"
    monkeypatch.setenv("CELEB_CODEX_HOME", "/tmp/.codex-y")
    assert resolve_codex_home(None) == "/tmp/.codex-y"


def test_a_directory_without_credentials_is_not_an_account(tmp_path):
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "auth.json").write_text("{}")
    (tmp_path / ".codex-backup").mkdir()          # no auth.json
    found = [p.name for p in discover_codex_homes(tmp_path)]
    assert found == [".codex"], found


def test_every_paid_script_lets_the_operator_choose_the_codex_account():
    """A judge that cannot be pointed at an account is a judge stuck on one."""
    for rel in ("scripts/score_evidenced.py", "scripts/run_stress.py",
                "scripts/measure_rater_noise.py", "scripts/score_pairings.py",
                "scripts/run_pilot.py"):
        src = (REPO / rel).read_text()
        if "CodexJudge(" not in src:
            continue
        assert "resolve_codex_home" in src, f"{rel} builds a CodexJudge without one"
