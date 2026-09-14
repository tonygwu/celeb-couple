"""A quota-spending script must not default to one hard-coded account.

Six scripts carried `--account` defaults pointing at `/Users/tonygwu/.claude-e`.
Two problems, both real rather than theoretical:

  - That path exists on exactly one machine. Every other checkout gets a
    default that cannot work.
  - Tonight `claude-e` was at 0% on its 5-hour window while `claude-c` had 66%
    fable headroom. A run taking the default would have burned its retries on
    `auth_or_quota` failures and reported them as a measurement problem.

The operator's own notes name this hard-coding as something that has already
broken four separate tools, and say the account list must be derived rather
than typed.

So there is no default. An unset account raises, names the config directories
it can actually see, and says to check `quotapick status` first.
"""
from __future__ import annotations

import pytest

from packages.llmkit.accounts import AccountNotChosen, resolve_account


def test_an_explicit_account_wins(tmp_path, monkeypatch):
    monkeypatch.setenv("CELEB_ACCOUNT", "/from/env")
    assert resolve_account(str(tmp_path)) == str(tmp_path)


def test_the_environment_variable_is_used_when_no_flag_is_given(monkeypatch):
    monkeypatch.setenv("CELEB_ACCOUNT", "/from/env")
    assert resolve_account(None) == "/from/env"


def test_an_unset_account_raises_rather_than_guessing(monkeypatch):
    monkeypatch.delenv("CELEB_ACCOUNT", raising=False)
    with pytest.raises(AccountNotChosen):
        resolve_account(None)


def test_the_error_names_the_accounts_it_can_see(monkeypatch, tmp_path):
    monkeypatch.delenv("CELEB_ACCOUNT", raising=False)
    for name in (".claude-b", ".claude-c"):
        (tmp_path / name).mkdir()
    with pytest.raises(AccountNotChosen) as e:
        resolve_account(None, home=tmp_path)
    msg = str(e.value)
    assert ".claude-b" in msg and ".claude-c" in msg, (
        "an error that does not say what the options are just moves the "
        "guessing onto the reader"
    )
    assert "quotapick" in msg, "headroom differs per account; say where to look"


def test_the_account_list_is_discovered_not_enumerated(monkeypatch, tmp_path):
    """The operator's notes: 'Assume there will be an F.' A helper that knows
    about b, c, d and e by name is the same bug as the hard-coded default."""
    monkeypatch.delenv("CELEB_ACCOUNT", raising=False)
    (tmp_path / ".claude-f").mkdir()
    with pytest.raises(AccountNotChosen) as e:
        resolve_account(None, home=tmp_path)
    assert ".claude-f" in str(e.value)


def test_no_script_carries_a_hardcoded_home_directory_default():
    """The regression itself, checked at the source."""
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    offenders = []
    for script in sorted((repo / "scripts").glob("*.py")):
        text = script.read_text()
        for line in text.splitlines():
            if "add_argument" in line and "account" in line and "/Users/" in line:
                offenders.append(f"{script.name}: {line.strip()}")
    assert not offenders, (
        "a quota-spending script defaults to one machine's account:\n  "
        + "\n  ".join(offenders))


def test_a_backup_directory_is_not_offered_as_an_account(tmp_path, monkeypatch):
    """`~/.claude-settings-backup-<stamp>` and `~/.claude-swap-backup` match the
    glob and are not accounts. The first version listed both."""
    monkeypatch.delenv("CELEB_ACCOUNT", raising=False)
    real = tmp_path / ".claude-c"
    real.mkdir()
    (real / "settings.json").write_text("{}")
    (tmp_path / ".claude-settings-backup-20260816T042158Z").mkdir()
    (tmp_path / ".claude-swap-backup").mkdir()
    from packages.llmkit.accounts import discover_accounts
    assert [p.name for p in discover_accounts(tmp_path)] == [".claude-c"]


def test_discovery_reports_something_rather_than_nothing(tmp_path, monkeypatch):
    """If no directory carries a marker, listing the glob matches still helps
    more than an empty list."""
    monkeypatch.delenv("CELEB_ACCOUNT", raising=False)
    (tmp_path / ".claude-odd").mkdir()
    from packages.llmkit.accounts import discover_accounts
    assert [p.name for p in discover_accounts(tmp_path)] == [".claude-odd"]


def test_a_dry_run_does_not_need_an_account():
    """Resolution happens where the judge is built, not at parse_args. The
    first wiring raised before the dry-run return, so `--dry-run` -- the one
    mode that spends nothing -- demanded an account it would never use."""
    import subprocess
    from pathlib import Path as _P
    repo = _P(__file__).resolve().parent.parent
    env = {"PATH": "/usr/bin:/bin", "HOME": str(_P.home())}
    r = subprocess.run(
        [str(repo / ".venv/bin/python"), str(repo / "scripts/measure_rater_noise.py"),
         "--dry-run", "--judges", "fable"],
        capture_output=True, text=True, cwd=repo, env=env, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "nothing spent" in r.stdout
