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


def test_every_free_analysis_script_is_in_the_chain():
    """gender_shape_confound.py was written and never added, so its artifact
    went stale relative to the others until someone ran it by hand."""
    from pathlib import Path as _P
    repo = _P(__file__).resolve().parent.parent
    paid = {"score_evidenced", "classify_romance", "extract_prose_mentions",
            "measure_rater_noise", "run_stress", "score_roster_joint",
            "run_pilot", "resolve_roster", "merge_prose_mentions",
            "scaling_report", "source_requirement", "reachable_products",
            "write_m0_report", "fetch_records", "build_episodes",
            "build_partner_universe", "fetch_observations",
            "fetch_onscreen_candidates"}
    for script in sorted((repo / "scripts").glob("*.py")):
        if script.stem in paid:
            continue
        assert script.name in CHAIN, (
            f"{script.name} is a free analysis script and is not in "
            "run_chain.sh, so its artifact will go stale relative to the others"
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


def test_the_prose_merge_runs_immediately_after_the_fetch():
    """fetch_observations.py REWRITES observations.json from the award and
    ranked tables alone, dropping any prose mentions previously folded in.

    Running it by hand cost this corpus 8 of its 41 observations with no error.
    The loss surfaced only because `audit_doc_numbers.py` caught "Women hold
    17" against a corpus that had quietly become 16 -- one guard catching the
    consequence of a different missing guard.

    Merging is idempotent, so the chain can simply always do it.
    """
    assert "merge_prose_mentions.py" in CHAIN
    assert CHAIN.index("fetch_observations.py") < CHAIN.index("merge_prose_mentions.py")
    assert CHAIN.index("merge_prose_mentions.py") < CHAIN.index("joint_coverage.py"), (
        "a merge after the analysis stages would leave them reading a thinner "
        "corpus than the one that gets published"
    )


def test_both_mention_files_are_merged():
    """Cohort mentions and partner mentions are separate files, and merging
    only one leaves the partner side of every pairing thinner."""
    assert "prose_mentions.json" in CHAIN
    assert "prose_mentions_partners.json" in CHAIN
