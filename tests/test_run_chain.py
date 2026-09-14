"""The chain script must encode the real dependency order, and must fail loudly."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CHAIN = (REPO / "scripts/run_chain.sh").read_text()


def test_the_free_stages_appear_in_dependency_order():
    order = ["fetch_records.py", "build_episodes.py", "build_partner_universe.py",
             "fetch_observations.py"]
    positions = [CHAIN.index(s) for s in order]
    assert positions == sorted(positions), (
        "a stage running before the one it depends on produces a stale answer "
        "rather than an error"
    )


def test_reports_run_after_the_data_stages():
    assert CHAIN.index("fetch_observations.py") < CHAIN.index("joint_coverage.py")
    assert CHAIN.index("joint_coverage.py") < CHAIN.index("write_m0_report.py")


def test_no_quota_spending_stage_is_in_the_convenience_script():
    """Burying a paid stage in a convenience script is how an unattended run
    empties a quota window."""
    for spender in ("score_evidenced", "classify_romance", "extract_prose_mentions",
                    "measure_rater_noise", "run_stress", "score_roster_joint"):
        assert f"{spender}.py" not in CHAIN, (
            f"{spender} spends model quota and must not run from run_chain.sh"
        )


def test_the_script_propagates_failure():
    assert 'exit "$fail"' in CHAIN
    assert "fail=1" in CHAIN, "a failing stage must set the exit status"


def test_the_script_is_executable_and_runs_from_any_directory():
    path = REPO / "scripts/run_chain.sh"
    assert path.stat().st_mode & 0o111, "run_chain.sh must be executable"
    assert 'cd "$(dirname "$0")/.."' in CHAIN, (
        "the script must resolve its own repo root, not depend on the caller's cwd"
    )


def test_it_reports_a_clean_run_distinctly_from_a_failed_one():
    assert "chain finished clean" in CHAIN
    assert "chain finished WITH FAILURES" in CHAIN
