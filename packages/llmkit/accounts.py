"""Which subscription account a quota-spending run should use.

No account is ever guessed. That is the rule, and it is not the same rule as
"there is no default", which is what this module used to say.

Six scripts used to default `--account` to `/Users/tonygwu/.claude-e`. That
path exists on one machine, and on the night this was written that account sat
at 0% on its 5-hour window while another had 66% headroom. A run taking the
default would have spent its retries on `auth_or_quota` failures, which look
like a broken judge rather than a full account.

Headroom moves between accounts hour by hour, so no value written into this
file can be right for long. That is an argument against a HARDCODED default,
and for years there was nothing else on offer, so the two looked identical.
They are not. A chooser that reads live usage at the moment of the run is not
guessing, and the Codex side now uses one: see `resolve_codex_home`. The Claude
side still refuses, because nothing has been wired up for it here yet.

The accounts are discovered by globbing, or asked of the router, rather than
listed by letter. The number of them changes, and a helper that knows about b,
c, d and e by name is the same bug one step removed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

__all__ = ["AccountNotChosen", "RouterUnavailable", "discover_accounts",
           "resolve_account", "DEFAULT_ACCOUNT", "discover_codex_homes",
           "resolve_codex_home", "CODEX_ENV_VAR", "ROUTER_BINARY",
           "ROUTER_CONTRACT_VERSION", "router_codex_accounts",
           "router_pick_codex_home"]

#: How to ask for the DEFAULT account, the one Claude Code uses when no
#: config dir is set.
#:
#: It cannot be named by a path. Its config file is `~/.claude.json`, which
#: sits OUTSIDE `~/.claude/`, so pointing CLAUDE_CONFIG_DIR at `~/.claude`
#: makes Claude Code look inside, find nothing, and scaffold a brand-new
#: EMPTY account. The run then fails as `auth_or_quota`, which reads as a
#: broken judge rather than a wrong account.
#:
#: The default account is therefore the ABSENCE of a config dir, and
#: `resolve_account` returns None for it so `ClaudeJudge` pops the variable.
DEFAULT_ACCOUNT = "default"

#: Read when `--account` is not passed. Lets a chain script set the account
#: once for several stages without every stage growing a flag.
ENV_VAR = "CELEB_ACCOUNT"


class AccountNotChosen(SystemExit):
    """Raised instead of picking an account that may have no quota left."""


def discover_accounts(home: Path | None = None) -> list[Path]:
    """Every Claude Code config directory visible in ``home``.

    Both the default `~/.claude` and the suffixed `~/.claude-b`, `~/.claude-c`
    and so on. Sorted, so the error message is stable.
    """
    h = Path(home) if home is not None else Path.home()
    found = {p for p in h.glob(".claude-*") if p.is_dir()}
    if (h / ".claude").is_dir():
        found.add(h / ".claude")
    # `.claude-settings-backup-<stamp>` and `.claude-swap-backup` match the
    # glob and are not accounts. Listing them as options in an error message
    # just moves the guessing onto the reader, so keep only directories that
    # carry a marker a real config dir has.
    real = {p for p in found
            if (p / "settings.json").exists() or (p / "projects").exists()}
    return sorted(real or found)


def resolve_account(flag: str | None, *, home: Path | None = None) -> str | None:
    """Return the config dir to run under, or raise naming the alternatives.

    Returns **None** for the default account, which is a choice and not a
    failure to choose: None means "unset CLAUDE_CONFIG_DIR", which is the only
    way to reach it. Raising still happens when nothing was chosen at all.
    """
    chosen = flag or os.environ.get(ENV_VAR)
    if chosen and chosen.strip().lower() == DEFAULT_ACCOUNT:
        return None
    if chosen:
        return chosen
    h = Path(home) if home is not None else Path.home()
    # The default account's directory is NOT offered as a path. Passing it
    # scaffolds an empty account; see DEFAULT_ACCOUNT. It is listed by its
    # keyword instead, so following this message cannot produce that failure.
    seen = [p for p in discover_accounts(home) if p != h / ".claude"]
    listed = ("\n  ".join(str(p) for p in seen) if seen
              else "(none found; is Claude Code installed for this user?)")
    raise AccountNotChosen(
        "No account chosen, and there is no default on purpose: quota headroom "
        "moves between accounts, and the account that was right yesterday can "
        "be at 0% today.\n\n"
        "Run `quotapick status` and pass the one with fable headroom:\n\n"
        f"  --account <config dir>      or   {ENV_VAR}=<config dir>\n"
        f"  --account {DEFAULT_ACCOUNT}           the account bare `claude` uses\n\n"
        f"Config directories visible here:\n  {listed}\n\n"
        f"`{DEFAULT_ACCOUNT}` is deliberately a keyword and not a path: the\n"
        f"default account's config is {h / '.claude.json'}, OUTSIDE\n"
        f"{h / '.claude'}, so passing that directory scaffolds an empty\n"
        f"account and the run fails as auth_or_quota.\n"
    )


#: Read when `--astra-account` is not passed.
CODEX_ENV_VAR = "CELEB_CODEX_HOME"


def discover_codex_homes(home: Path | None = None) -> list[Path]:
    """Every Codex account directory visible in ``home``.

    A Codex account IS a CODEX_HOME directory, the way a Claude account is a
    CLAUDE_CONFIG_DIR. Unlike the Claude side there is no trap here: `~/.codex`
    is a real account directory holding its own `config.toml` and `auth.json`,
    so it can be named by path like any other.

    Discovered by globbing rather than listed by letter, for the same reason as
    ``discover_accounts``: the number of accounts changes.
    """
    h = Path(home) if home is not None else Path.home()
    found = {p for p in h.glob(".codex-*") if p.is_dir()}
    if (h / ".codex").is_dir():
        found.add(h / ".codex")
    # An account has credentials. A stray `.codex-backup` does not.
    real = {p for p in found if (p / "auth.json").exists()}
    return sorted(real or found)


#: The quota router: a separate tool (`tonygwu/llm-quota-router`) that reads
#: LIVE per-account usage. It is what makes a Codex default safe at last. The
#: objection to a default was never "choosing is wrong", it was that no value
#: written into this file can know which account has quota at the moment it
#: runs. The router asks.
ROUTER_BINARY = "quotapick"

#: The only router contract this parser has been read against.
#:
#: The router ships from its own repository on its own release cycle, so its
#: JSON can move without anything here changing. A parser that reads an unknown
#: shape and finds no `fits` key would conclude "not fitting" and refuse, which
#: is survivable, or worse, find a key that has been repurposed. Refuse on an
#: unrecognised version instead and say so.
ROUTER_CONTRACT_VERSION = 1

#: Ceiling on one router call. Measured 2026-09-15 against the live endpoint:
#: `status --json` 4.2s, `pick` 1.0s. The ceiling is generous because the
#: alternative to waiting is refusing a run the operator asked for, and this
#: resolves ONCE per run rather than once per judged unit.
ROUTER_TIMEOUT_S = 30.0


class RouterUnavailable(AccountNotChosen):
    """The router could not name an account with quota.

    A subclass of ``AccountNotChosen`` on purpose: from a caller's point of
    view nothing has changed. No account was chosen, so the run refuses to
    start rather than spending its retries on `auth_or_quota`.
    """


def _router_json(args: list[str], *, timeout: float = ROUTER_TIMEOUT_S) -> dict:
    """One router call, parsed and version-checked.

    **The exit code proves nothing here**, and this is measured rather than
    assumed. On 2026-09-15 `quotapick pick` exited 0 while returning an account
    at 0.0% remaining, and exited 0 again when it could see no accounts at all
    and returned `"account": null`. Every decision below is taken on the body.
    """
    exe = shutil.which(ROUTER_BINARY)
    if exe is None:
        raise RouterUnavailable(
            f"`{ROUTER_BINARY}` is not on PATH, so the Codex account cannot be "
            f"chosen for you.\n\n"
            f"Install it, or name the account yourself:\n\n"
            f"  --astra-account <codex home>   or   {CODEX_ENV_VAR}=<codex home>\n"
        )
    printable = " ".join([ROUTER_BINARY, *args])
    try:
        proc = subprocess.run([exe, *args], capture_output=True, text=True,
                              timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as exc:
        raise RouterUnavailable(
            f"`{printable}` did not answer within {timeout:g}s. It reads live "
            f"usage endpoints, so a hung network call looks like this. Name "
            f"the account yourself to skip it: {CODEX_ENV_VAR}=<codex home>"
        ) from exc
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RouterUnavailable(
            f"`{printable}` exited {proc.returncode} and its output is not "
            f"JSON.\n  stdout: {proc.stdout[:300]!r}\n"
            f"  stderr: {proc.stderr[:300]!r}"
        ) from exc
    got = payload.get("contract_version")
    if got != ROUTER_CONTRACT_VERSION:
        raise RouterUnavailable(
            f"`{printable}` speaks contract_version {got!r}; this parser was "
            f"written against {ROUTER_CONTRACT_VERSION} and will not guess at "
            f"a shape it has not read. Update packages/llmkit/accounts.py, or "
            f"name the account yourself with {CODEX_ENV_VAR}=<codex home>."
        )
    return payload


def router_codex_accounts(*, timeout: float = ROUTER_TIMEOUT_S) -> list[str]:
    """Every account id the ROUTER classifies as Codex, newest knowledge first.

    Derived from `status --json`, not written down. The change request that
    added this named the accounts directly, as `--only codex,codex_b`, and
    those two ids are correct today. Writing them here would be the bug in this
    module's own docstring one step removed: a third Codex account would be
    invisible to the picker, silently, while `quotapick status` listed it.
    """
    payload = _router_json(["status", "--json"], timeout=timeout)
    ids = sorted({a["id"] for a in payload.get("accounts") or []
                  if a.get("provider") == "codex" and a.get("id")})
    if not ids:
        raise RouterUnavailable(
            f"`{ROUTER_BINARY} status` knows no account with provider "
            f"\"codex\", so there is nothing to choose between. Configure one "
            f"there, or name the home yourself with {CODEX_ENV_VAR}=<codex home>."
        )
    return ids


def router_pick_codex_home(*, timeout: float = ROUTER_TIMEOUT_S) -> tuple[str, str]:
    """``(account id, CODEX_HOME)`` for the Codex account with most headroom.

    Refuses rather than returning an exhausted account. That guard is the whole
    reason this function is longer than one line: see ``_fits`` below.
    """
    ids = router_codex_accounts(timeout=timeout)
    payload = _router_json(
        ["pick", "--only", ",".join(ids), "--dry-run", "--json"], timeout=timeout)
    decision = payload.get("decision") or {}
    reason = decision.get("reason") or "(the router gave no reason)"
    account = decision.get("account")
    if not account:
        raise RouterUnavailable(
            f"`{ROUTER_BINARY}` named no Codex account among {', '.join(ids)}: "
            f"{reason}"
        )

    # A RETURNED ACCOUNT IS NOT A SPENDABLE ONE. Measured 2026-09-15: the
    # router answered exit 0, `"account": "codex"`, `"reason": "every candidate
    # is out of quota; earliest reset in 5.0h"` -- and `fits: false`.
    #
    # `fits: false` does NOT mean the call would fail. A smoke test spent a
    # real `codex exec` call against that same account minutes later and got a
    # normal verdict back. The first version of this comment concluded from
    # that the reading was a stale transcript estimate, and the router's
    # maintainer corrected it: the reading was live, confidence 1.0, age 0s.
    # Codex quota is a live rate-limit read from the codex app-server, with
    # session transcripts kept only as the FALLBACK when that read fails. Do
    # not read the correction as "transcripts are gone" either; both halves of
    # that sentence have now been got wrong once each.
    #
    # The account is held back ON PURPOSE. The operator sets a manual reserve
    # on `codex`, because the Codex DESKTOP app can only use ~/.codex and needs
    # weekly quota left for interactive work. At the time of measurement the
    # vendor had 13% of the weekly pool left, the reserve held 51%, and 0% was
    # spendable by automation. `quotapick status --explain` prints that split:
    #
    #   reserve codex: 13% left - 51% held for manual use = 0% spendable
    #
    # So spending it is worse than a failed run, not better. A failed run is
    # loud. Quietly eating the reserve takes the operator's interactive quota
    # and nothing reports it. `fits` is the whole reserve mechanism, and an
    # automated caller that ignores it defeats a policy rather than dodging an
    # outage.
    if not (decision.get("fits") and decision.get("meets_policy")):
        raise RouterUnavailable(
            f"`{ROUTER_BINARY}` returned {account} but reports it unusable "
            f"(fits={decision.get('fits')!r}, "
            f"meets_policy={decision.get('meets_policy')!r}): {reason}\n\n"
            f"Refusing. `fits: false` can mean the vendor window is spent, or "
            f"that the operator holds this account in reserve for interactive "
            f"use; `quotapick status --explain` says which. Wait for the reset, "
            f"or override with {CODEX_ENV_VAR}=<codex home> if you know better."
        )

    # Belt and braces on the `--only` filter. CODEX_HOME pointed at a Claude
    # config dir would not fail loudly; it would start a Codex judge on a
    # directory with no Codex credentials.
    if decision.get("provider") != "codex":
        raise RouterUnavailable(
            f"`{ROUTER_BINARY}` chose {account}, whose provider is "
            f"{decision.get('provider')!r} and not \"codex\". Refusing to set "
            f"CODEX_HOME from it."
        )

    codex_home = ((payload.get("exec") or {}).get("env") or {}).get("CODEX_HOME")
    if not codex_home:
        raise RouterUnavailable(
            f"`{ROUTER_BINARY}` chose {account} but returned no "
            f"exec.env.CODEX_HOME to run it under."
        )
    return account, codex_home


def resolve_codex_home(flag: str | None = None, *, home: Path | None = None,
                       pick=None) -> str:
    """Return the CODEX_HOME to run under, or raise naming the alternatives.

    The order is: the flag, then the environment variable, then **ask the
    router**. It no longer refuses when nothing is named, because something
    that reads live usage can now answer the question, and an operator picking
    by hand from yesterday's memory is the failure this module exists about.

    What has NOT changed is that nothing here guesses. If the router cannot
    name an account with quota, this still refuses; it does not fall back to
    ~/.codex. An inherited CODEX_HOME is a hidden choice rather than an
    explicit one, and that was true before the router existed.

    ``pick`` is the seam the tests use. It takes no arguments and returns
    ``(account id, CODEX_HOME)``.
    """
    chosen = flag or os.environ.get(CODEX_ENV_VAR)
    if chosen:
        return chosen
    try:
        account, codex_home = (pick or router_pick_codex_home)()
    except RouterUnavailable as exc:
        # Every refusal above ends by offering the manual override, so the
        # homes on THIS machine are the missing half of that offer. Appending
        # them here is why this function still takes `home`.
        seen = discover_codex_homes(home)
        listed = ("\n  ".join(str(p) for p in seen) if seen
                  else "(none found; is Codex installed for this user?)")
        raise RouterUnavailable(
            f"{exc}\n\nCodex homes visible here:\n  {listed}\n") from exc
    # The choice is announced. A router picking silently would be an inherited
    # CODEX_HOME with extra steps, and the operator could not tell afterwards
    # which account paid for the run.
    print(f"[accounts] {ROUTER_BINARY} chose Codex account {account} "
          f"(CODEX_HOME={codex_home})", file=sys.stderr)
    return codex_home
