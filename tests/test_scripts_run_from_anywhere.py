"""Every script must run from any directory, not just the repository root.

AGENTS.md rule 6: committed code must run from any checkout, any machine, any
environment. The suite runs from the repo root, so a script that resolves its
imports off the current working directory passes every test and fails the
moment somebody runs it by absolute path -- from a cron entry, from another
clone, or from a shell that happens to be somewhere else.

Caught exactly that during the User-Agent consolidation. resolve_roster.py had
imported nothing from the repo, so it had no `sys.path.insert` line; adding one
import broke it everywhere but the root, and the full suite stayed green.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

#: Scripts with no argparse, so `--help` is not a cheap no-op for them.
_NO_ARGPARSE: frozenset[str] = frozenset()


def _scripts():
    return sorted(p for p in (REPO / "scripts").glob("*.py")
                  if p.stem not in _NO_ARGPARSE)


@pytest.mark.parametrize("script", _scripts(), ids=lambda p: p.name)
def test_the_script_starts_from_an_unrelated_directory(script):
    """`--help` exercises every import and nothing else.

    It spends no quota and touches no network: argparse prints and exits before
    any of that. What it proves is that the module body -- which is where the
    imports live -- runs with the working directory somewhere else entirely.
    """
    with tempfile.TemporaryDirectory() as cwd:
        # sys.executable, never a checked-in interpreter path: CI installs
        # with setup-python and has no local virtualenv, and three tests once
        # failed for exactly that reason. tests/test_scripts_safe.py enforces
        # it, and rejects the literal path even inside a comment -- which is
        # why this one describes it instead of spelling it.
        r = subprocess.run([sys.executable, str(script), "--help"],
                           cwd=cwd, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, (
        f"{script.name} fails to start from {cwd}:\n"
        f"{r.stderr.strip()[-600:]}"
    )


def test_there_are_scripts_to_check():
    """A glob that matches nothing would make every test above vacuous."""
    assert len(_scripts()) > 20
