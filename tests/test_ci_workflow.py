"""The CI workflow has never executed, so nothing validates it.

Every run of `.github/workflows/tests.yml` has been refused at GitHub's billing
gate before reaching pytest, so the repository's Actions state is red while the
suite is green, and the workflow file itself is unexercised. A typo in it would
be invisible until the day billing is fixed -- and on that day it would look
like the tests broke.

These tests check the parts that would silently stop the gate from gating.
They do not need Actions to run.

Verified alongside them, by hand on 2026-09-14: a fresh clone with
`python3 -m venv`, `pip install -r requirements.txt` and `python -m pytest
tests -q` exits 0, and it still exits 0 with the network blocked by an
unroutable proxy. The suite is offline, as the workflow assumes.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github/workflows/tests.yml"


@pytest.fixture(scope="module")
def text() -> str:
    if not WORKFLOW.exists():
        pytest.skip("no CI workflow in this checkout")
    return WORKFLOW.read_text()


def test_it_runs_pytest_through_the_interpreter(text):
    """`python -m pytest` and not bare `pytest`.

    A bare `pytest` resolves off PATH and can silently be a different
    interpreter's, which is the class of bug AGENTS.md rule 6 is about.
    """
    assert re.search(r"python -m pytest\s+tests", text), (
        "the workflow must run the suite as `python -m pytest tests`")
    assert not re.search(r"^\s*(run:\s*)?pytest\s", text, re.M), (
        "bare `pytest` resolves off PATH")


def test_it_installs_from_requirements(text):
    assert "pip install -r requirements.txt" in text
    assert (REPO / "requirements.txt").exists(), (
        "the workflow installs a file that is not in the repository")


def test_it_does_not_swallow_the_exit_status(text):
    """`pytest | tail` reports tail's status, and that pushed a red suite twice.

    The rule is in AGENTS.md. A workflow that broke it would report green while
    the suite failed, which is worse than the current red-for-billing.
    """
    for line in text.splitlines():
        if "pytest" in line:
            assert "|" not in line or "pipefail" in text, (
                f"pytest's status is read through a pipe: {line.strip()!r}")
            assert not re.search(r"pytest.*;\s*echo", line), (
                f"pytest's status is discarded: {line.strip()!r}")
            assert "|| true" not in line and "|| :" not in line, (
                f"pytest's failure is suppressed: {line.strip()!r}")


def test_it_pins_a_python_version_the_project_supports(text):
    """The project targets 3.12. An unpinned runner silently moves."""
    m = re.search(r'python-version:\s*"?(\d+\.\d+)"?', text)
    assert m, "the workflow must pin a Python version"
    assert m.group(1) == "3.12", f"workflow pins {m.group(1)}, the project is 3.12"


def test_it_actually_triggers(text):
    """A workflow with no trigger never runs, which looks identical to the
    billing block it is currently behind."""
    assert re.search(r"^on:", text, re.M)
    assert "pull_request" in text or "push" in text


def test_no_test_in_this_suite_requires_the_network(text):
    """The workflow's comment claims the suite is offline; it is load-bearing.

    Checked by construction rather than by running: a test that reaches the
    internet would be flaky in CI and slow everywhere. Anything that does need
    a network lives in scripts/, never in tests/.
    """
    offenders = []
    for p in sorted((REPO / "tests").glob("*.py")):
        body = p.read_text()
        for m in re.finditer(r"urllib\.request\.urlopen|requests\.(get|post)\(", body):
            line = body[: m.start()].count("\n") + 1
            offenders.append(f"{p.name}:{line}")
    assert offenders == [], (
        "these tests make live HTTP calls; the workflow assumes an offline "
        "suite: " + ", ".join(offenders))
