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


def test_every_required_artifact_names_the_command_that_makes_it():
    """PRODUCERS said "Keep in step with AGENTS.md", which is a manual
    invariant and therefore one that drifts. Seven artifacts had no entry and
    fell through to the generic "the pipeline stage that writes it", which is
    exactly the unhelpful message the module exists to replace.

    A fresh clone has no data/. Every one of these paths WILL be missing there,
    so the error message is the whole user interface for that situation.
    """
    import re
    from pathlib import Path as _P
    from packages.llmkit.artifacts import PRODUCERS

    repo = _P(__file__).resolve().parent.parent
    pattern = re.compile(r'require\((?:REPO|repo), "([^"]+)"\)')
    required = set()
    for d in ("scripts", "modules", "packages"):
        for f in (repo / d).rglob("*.py"):
            required.update(pattern.findall(f.read_text()))

    missing = sorted(required - set(PRODUCERS))
    assert not missing, (
        "artifacts required with no entry in PRODUCERS, so a fresh clone is "
        "told only that 'the pipeline stage that writes it' produces them:\n  "
        + "\n  ".join(missing))


def test_no_test_hardcodes_the_local_venv_interpreter():
    """CI installs with setup-python and has no `.venv` at all.

    Three tests spawned `repo/.venv/bin/python`, so they would have failed on
    the first CI run — and CI has never run, because it is blocked on the
    account's billing. A local simulation of the workflow found it: clone into
    a scratch directory, `python3 -m venv`, `pip install -r requirements.txt`,
    `pytest tests -q`.

    One of them also SKIPPED when `.venv` was missing, which is worse than
    failing: the guard would have been silently inert in the one environment it
    was meant to protect.
    """
    from pathlib import Path as _P
    repo = _P(__file__).resolve().parent.parent
    offenders = []
    for f in sorted((repo / "tests").glob("*.py")):
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if ".venv/bin/python" in line:
                offenders.append(f"{f.name}:{i}: {line.strip()}")
    assert not offenders, (
        "use sys.executable; CI has no .venv:\n  " + "\n  ".join(offenders))
