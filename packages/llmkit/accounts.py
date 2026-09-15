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
           "DEFAULT_ACCOUNT"]

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
