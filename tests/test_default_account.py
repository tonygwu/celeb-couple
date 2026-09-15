"""The default account is reachable, and its directory is never offered as a path.

The fleet's largest fable reserve sat on the account bare `claude` uses, and no
paid script could ask for it: `resolve_account` took a config-dir path, and that
account is the ABSENCE of `CLAUDE_CONFIG_DIR` rather than a value for it.

Worse, the refusal message listed `~/.claude` among the valid choices. Following
that advice sets `CLAUDE_CONFIG_DIR=~/.claude`, which makes Claude Code look
inside the directory, find no config (the real one is `~/.claude.json`, outside
it), and scaffold a brand-new EMPTY account. The run then fails as
`auth_or_quota`, which reads as a broken judge rather than a wrong account --
the same failure shape as the hardcoded default this module was written to
remove, relocated into its own error text.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.accounts import (AccountNotChosen,  # noqa: E402
                                      DEFAULT_ACCOUNT, resolve_account)
from packages.llmkit.judges import ClaudeJudge  # noqa: E402


@pytest.fixture
def no_env(monkeypatch):
    monkeypatch.delenv("CELEB_ACCOUNT", raising=False)


def test_the_keyword_resolves_to_no_config_dir(no_env):
    # None is the POINT: it is what makes ClaudeJudge unset the variable.
    assert resolve_account(DEFAULT_ACCOUNT) is None


def test_the_keyword_is_case_insensitive_and_tolerates_whitespace(no_env):
    assert resolve_account(" Default ") is None
    assert resolve_account("DEFAULT") is None


def test_it_works_through_the_environment_variable_too(monkeypatch):
    monkeypatch.setenv("CELEB_ACCOUNT", DEFAULT_ACCOUNT)
    assert resolve_account(None) is None


def test_a_real_config_dir_is_still_returned_unchanged(no_env):
    assert resolve_account("/tmp/.claude-z") == "/tmp/.claude-z"


def test_choosing_nothing_still_refuses(no_env):
    with pytest.raises(AccountNotChosen):
        resolve_account(None)


def test_the_refusal_never_offers_the_default_accounts_directory(no_env, tmp_path):
    """The message must not recommend the value that scaffolds an empty account."""
    for name in (".claude", ".claude-b", ".claude-c"):
        d = tmp_path / name
        d.mkdir()
        (d / "settings.json").write_text("{}")
    with pytest.raises(AccountNotChosen) as e:
        resolve_account(None, home=tmp_path)
    msg = str(e.value)
    assert str(tmp_path / ".claude-b") in msg, "real accounts must still be listed"
    # Matched LINE-EXACT, not by substring: `.claude-b` contains `.claude`, so a
    # substring check reports a violation that is not there. (It did, on the
    # first run of this test.) The directory may still appear in the prose
    # explaining WHY it is not an option, so only the listing is examined.
    listed = msg.split("Config directories visible here:")[1].split("`default` is")[0]
    entries = [ln.strip() for ln in listed.splitlines() if ln.strip()]
    assert str(tmp_path / ".claude") not in entries, entries
    assert DEFAULT_ACCOUNT in msg


def test_the_judge_unsets_the_variable_for_the_default_account(monkeypatch):
    """End to end: the keyword must actually produce an environment with no
    CLAUDE_CONFIG_DIR, or the fix stops at the boundary of this module."""
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", "/some/other/account")
    judge = ClaudeJudge("fable", "claude-fable-5-1",
                        config_dir=resolve_account(DEFAULT_ACCOUNT))
    assert "CLAUDE_CONFIG_DIR" not in judge._env()


def test_a_named_account_still_sets_the_variable(monkeypatch):
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    judge = ClaudeJudge("fable", "claude-fable-5-1",
                        config_dir=resolve_account("/tmp/.claude-z"))
    assert judge._env()["CLAUDE_CONFIG_DIR"] == "/tmp/.claude-z"
