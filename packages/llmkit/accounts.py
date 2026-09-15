"""Which subscription account a quota-spending run should use.

There is deliberately no default.

Six scripts used to default `--account` to `/Users/tonygwu/.claude-e`. That
path exists on one machine, and on the night this was written that account sat
at 0% on its 5-hour window while another had 66% headroom. A run taking the
default would have spent its retries on `auth_or_quota` failures, which look
like a broken judge rather than a full account.

Headroom moves between accounts hour by hour, so no value written into this
file can be right for long. The accounts are discovered by globbing rather than
listed by letter, because the number of them changes and a helper that knows
about b, c, d and e by name is the same bug one step removed.
"""

from __future__ import annotations

import os
from pathlib import Path

__all__ = ["AccountNotChosen", "discover_accounts", "resolve_account",
           "DEFAULT_ACCOUNT", "discover_codex_homes", "resolve_codex_home",
           "CODEX_ENV_VAR"]

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


def resolve_codex_home(flag: str | None, *, home: Path | None = None) -> str:
    """Return the CODEX_HOME to run under, or raise naming the alternatives.

    There is no default, for the reason the module docstring gives, and for a
    sharper one measured on 2026-09-15: ``CodexJudge`` passed NO environment to
    its subprocess, so every call silently inherited the shell's CODEX_HOME and
    landed on ~/.codex. A second account with a FULL weekly window sat
    unreachable while runs failed on the exhausted one. An implicit account is
    not a default, it is a hidden one.
    """
    chosen = flag or os.environ.get(CODEX_ENV_VAR)
    if chosen:
        return chosen
    seen = discover_codex_homes(home)
    listed = ("\n  ".join(str(p) for p in seen) if seen
              else "(none found; is Codex installed for this user?)")
    raise AccountNotChosen(
        "No Codex account chosen, and there is no default on purpose: the "
        "account that was right yesterday can be at 0% today, and an inherited "
        "CODEX_HOME is a hidden choice rather than an explicit one.\n\n"
        "Run `quotapick status` and pass the one with headroom:\n\n"
        f"  --astra-account <codex home>   or   {CODEX_ENV_VAR}=<codex home>\n\n"
        f"Codex homes visible here:\n  {listed}\n"
    )
