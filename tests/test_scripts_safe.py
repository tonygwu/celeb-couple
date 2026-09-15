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

    Three tests spawned the repository-local virtualenv interpreter directly,
    so they would have failed on the first CI run — and CI has never run, because it is blocked on the
    account's billing. A local simulation of the workflow found it: clone into
    a scratch directory, `python3 -m venv`, `pip install -r requirements.txt`,
    `pytest tests -q`.

    One of them also SKIPPED when `.venv` was missing, which is worse than
    failing: the guard would have been silently inert in the one environment it
    was meant to protect.
    """
    from pathlib import Path as _P
    repo = _P(__file__).resolve().parent.parent
    needle = ".venv" + "/bin/python"      # split so this file is not its own hit
    offenders = []
    for f in sorted((repo / "tests").glob("*.py")):
        if f.name == Path(__file__).name:
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if needle in line:
                offenders.append(f"{f.name}:{i}: {line.strip()}")
    assert not offenders, (
        "use sys.executable; CI has no .venv:\n  " + "\n  ".join(offenders))


def test_the_agents_tool_table_is_one_unbroken_table():
    """A prose paragraph was inserted into the middle of the table, orphaning
    every row after it — including all six quota-spending scripts, which are
    the ones an agent most needs to find before running something expensive.
    Markdown renders the tail as plain text or a second table."""
    from pathlib import Path as _P
    repo = _P(__file__).resolve().parent.parent
    lines = (repo / "AGENTS.md").read_text().splitlines()
    start = next(i for i, l in enumerate(lines) if l.startswith("| Command |"))
    rows = 0
    for line in lines[start:]:
        if line.startswith("|"):
            rows += 1
        elif line.strip() == "":
            continue
        else:
            break
    assert rows >= 25, (
        f"only {rows} contiguous rows after the table header; something has "
        "been inserted into the middle of the table")


def test_every_script_appears_in_the_agents_table():
    """An unregistered tool exists for nobody — AGENTS.md says so itself."""
    import subprocess
    from pathlib import Path as _P
    repo = _P(__file__).resolve().parent.parent
    table = (repo / "AGENTS.md").read_text()
    scripts = subprocess.run(["git", "ls-files", "scripts/*.py"], cwd=repo,
                             capture_output=True, text=True, check=True).stdout.split()
    missing = [s for s in scripts if _P(s).name not in table]
    assert not missing, f"scripts not registered in AGENTS.md: {missing}"


def test_a_spender_checks_its_inputs_before_it_spends():
    """A guard that fires after the model calls is a receipt, not a guard.

    `run_stress.py` reads the rater-noise floor from a separate scoring run.
    That read only happens in the analysis at the END, so when the floor was
    given a stale-contract check the script would have spent about 27 calls and
    THEN refused. The check is now made before the judges are built.

    Asserted on source order rather than by running the script, because
    exercising it for real would mean spending the quota this test exists to
    protect.
    """
    src = (REPO / "scripts/run_stress.py").read_text()
    body = src[src.index("def main("):]
    check = body.index("measured_floor()")
    first_judge = min(body.index("ClaudeJudge("), body.index("CodexJudge("))
    assert check < first_judge, (
        "run_stress.py builds a judge before checking the rater-noise floor. "
        "A stale floor would then be found after the calls were already spent."
    )


def test_no_paid_script_defaults_an_account_to_a_machine_absolute_path():
    """A default that is wrong is worse than no default.

    `accounts.py` was written because six scripts defaulted `--account` to
    `/Users/tonygwu/.claude-e`, a path that exists on one machine and was at 0%
    quota the night it was found. The fix removed it from five of them.
    `score_evidenced.py` kept it AND bypassed `resolve_account`, so the refusal
    never fired there, until 2026-09-15.

    Prose may still describe the history; this checks argparse DEFAULTS.
    """
    import ast
    offenders = []
    for path in sorted((REPO / "scripts").glob("*.py")):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "add_argument"):
                continue
            names = [a.value for a in node.args if isinstance(a, ast.Constant)]
            if not any(isinstance(n, str) and "account" in n for n in names):
                continue
            for kw in node.keywords:
                if kw.arg != "default":
                    continue
                for sub in ast.walk(kw.value):
                    if (isinstance(sub, ast.Constant) and isinstance(sub.value, str)
                            and sub.value.startswith("/")):
                        offenders.append(f"{path.name}: --account default {sub.value!r}")
    assert not offenders, (
        "account defaults pointing at one machine:\n  " + "\n  ".join(offenders)
        + "\nUse resolve_account / resolve_codex_home, which refuse and name "
          "the alternatives.")
