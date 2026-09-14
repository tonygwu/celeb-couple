"""Every script must answer --help without doing anything.

score_evidenced.py had no argparse, so `--help` was treated as a normal
invocation and BEGAN A SCORING RUN: it spent model quota to answer a question
about its own usage, and the only sign was that the command did not come back.

A script that can spend money or quota must be safe to ask about.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = sorted(p for p in (REPO / "scripts").glob("*.py"))
#: These reach the network or a model the moment they run, so a --help that
#: does not return immediately means the guard is missing.
SPENDERS = {
    "score_evidenced.py", "classify_romance.py", "extract_prose_mentions.py",
    "measure_rater_noise.py", "run_stress.py", "score_roster_joint.py",
    "run_pilot.py",
}


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_help_returns_promptly_and_does_nothing(script: Path):
    proc = subprocess.run([sys.executable, str(script), "--help"],
                          cwd=str(REPO), capture_output=True, text=True,
                          timeout=25)
    assert proc.returncode == 0, (
        f"{script.name} --help exited {proc.returncode}; a script that can spend "
        f"quota must be safe to ask about\n{proc.stderr[-400:]}"
    )
    assert "usage:" in proc.stdout.lower(), f"{script.name} printed no usage"


def test_every_spender_declares_that_it_spends():
    """The help text is where somebody decides whether to run it."""
    for name in sorted(SPENDERS):
        path = REPO / "scripts" / name
        if not path.exists():
            continue
        proc = subprocess.run([sys.executable, str(path), "--help"],
                              cwd=str(REPO), capture_output=True, text=True,
                              timeout=25)
        blob = (proc.stdout + proc.stderr).lower()
        assert "quota" in blob or "spend" in blob or "model call" in blob, (
            f"{name} spends model quota and its --help does not say so"
        )
