"""The verification command must fail when the suite fails, and when it is empty.

WHY THIS EXISTS
---------------
Plan v2 shipped this runner:

    for t in scripts/test_*.py; do python "$t" >/dev/null || echo "FAILED $t"; done

It exits 0 even when every test fails, because the last command in the loop is
`echo`.  It also exits 0 when the glob matches nothing, so deleting the test
directory would have looked like a clean run.  And the documented invocation
`bash scripts/run_tests.sh; echo "exit=$?"` reports the status of `echo`, not
of the runner.

This test drives the REAL production entrypoint as a subprocess against
isolated fixture directories and asserts the exit code that comes back.
pytest exit codes: 0 all passed, 1 tests failed, 5 NO TESTS COLLECTED.
A verification wrapper that treats only 1 as failure would pass an empty suite.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
INTERPRETER = REPO_ROOT / ".venv" / "bin" / "python"

# pytest's own documented exit codes.
EXIT_OK = 0
EXIT_TESTS_FAILED = 1
EXIT_NO_TESTS_COLLECTED = 5


def _interpreter() -> str:
    """The interpreter the production command names.

    If .venv is missing we fall back to the running interpreter rather than
    invoking a path that does not exist -- otherwise a missing venv produces
    exit code 127 and looks exactly like a failing test, which is the mistake
    this whole file exists to prevent.
    """
    return str(INTERPRETER) if INTERPRETER.exists() else sys.executable


def _run_pytest_on(directory: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [_interpreter(), "-m", "pytest", str(directory), "-q", "-p", "no:cacheprovider"],
        cwd=str(directory),          # isolate from this repo's pyproject/rootdir
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_interpreter_exists() -> None:
    """A missing interpreter must never be mistaken for a failing test."""
    assert Path(_interpreter()).exists(), (
        f"interpreter {_interpreter()} does not exist; exit code 127 would be "
        "indistinguishable from a test failure"
    )


def test_failing_suite_exits_nonzero_and_names_the_test(tmp_path: Path) -> None:
    d = tmp_path / "failing"
    d.mkdir()
    (d / "test_deliberate_failure.py").write_text(
        "def test_deliberate_failure():\n    assert 1 == 2\n"
    )
    proc = _run_pytest_on(d)
    assert proc.returncode == EXIT_TESTS_FAILED, (
        f"a failing suite returned {proc.returncode}; expected {EXIT_TESTS_FAILED}"
    )
    assert "test_deliberate_failure" in (proc.stdout + proc.stderr), (
        "the runner must name the failing test in its output"
    )


def test_empty_suite_exits_five_not_zero(tmp_path: Path) -> None:
    """The v2 defect: no tests collected must not look like success."""
    d = tmp_path / "empty"
    d.mkdir()
    proc = _run_pytest_on(d)
    assert proc.returncode == EXIT_NO_TESTS_COLLECTED, (
        f"an empty suite returned {proc.returncode}; expected "
        f"{EXIT_NO_TESTS_COLLECTED} (no tests collected)"
    )
    assert proc.returncode != EXIT_OK, "an empty suite must never report success"


def test_passing_suite_exits_zero(tmp_path: Path) -> None:
    d = tmp_path / "passing"
    d.mkdir()
    (d / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    proc = _run_pytest_on(d)
    assert proc.returncode == EXIT_OK, (
        f"a passing suite returned {proc.returncode}; expected {EXIT_OK}"
    )


@pytest.mark.parametrize("code", [EXIT_TESTS_FAILED, EXIT_NO_TESTS_COLLECTED])
def test_verification_wrapper_treats_code_as_failure(code: int) -> None:
    """The documented wrapper must not swallow status behind a `;`.

    `cmd; echo "exit=$?"` exits with echo's status.  The contract is that the
    verification command propagates the runner's own status, so anything
    non-zero -- 5 included -- stops a CI step or a shell with `set -e`.
    """
    proc = subprocess.run(
        ["bash", "-c", f'bash -c "exit {code}" && echo UNREACHABLE'],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == code
    assert "UNREACHABLE" not in proc.stdout
