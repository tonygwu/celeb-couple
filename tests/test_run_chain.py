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

    # Spenders are DERIVED from the declaration, not listed. This was a
    # hardcoded set of 16 names, and plan v4's score_pairings.py -- which says
    # SPENDS MODEL QUOTA in its own description -- was reported as a free
    # script missing from the chain. Third time a pinned set in this repo went
    # stale after the set grew. tests/test_scripts_safe.py already enforces
    # that every spender declares itself, so the declaration is trustworthy.
    def _spends(path) -> bool:
        return "SPENDS MODEL QUOTA" in path.read_text()

    #: Free, and deliberately NOT in the chain. Each needs a reason: an
    #: exemption without one is how a guard rots into a formality.
    outside = {
        "resolve_roster": "run once to build the roster; not an analysis stage",
        "merge_prose_mentions": "the chain calls it per mentions file, in a loop",
        "scaling_report": "gated inside the chain on the roster artifacts existing",
        "write_m0_report": "in the chain, under its reports pass",
        "fetch_records": "in the chain, under its free pass",
        "build_episodes": "in the chain, under its free pass",
        "build_partner_universe": "in the chain, under its free pass",
        "fetch_observations": "in the chain, under its free pass",
        "fetch_onscreen_candidates": "in the chain, under its free pass",
        "select_m1_slice": "plan v4; picked once before judging, not a recurring stage",
        "expand_roster": ("builds a ROSTER, which is an input to the chain and "
                          "not a stage of it. Re-snowballing on every free pass "
                          "would move the cohort under the artifacts derived "
                          "from it, which is the opposite of what the chain is "
                          "for. Run it deliberately, like resolve_roster."),
    }
    scripts = sorted((repo / "scripts").glob("*.py"))
    assert len(scripts) > 20, (
        f"the glob found {len(scripts)} scripts; a broken glob makes this "
        "guard pass while checking nothing")
    for script in scripts:
        if _spends(script) or script.stem in outside:
            continue
        assert script.name in CHAIN, (
            f"{script.name} is a free analysis script and is not in "
            "run_chain.sh, so its artifact will go stale relative to the others"
        )


def test_every_exemption_names_a_script_that_exists():
    from pathlib import Path as _P
    repo = _P(__file__).resolve().parent.parent
    # An exemption for a renamed script silently stops covering the new name.
    for stem in ("resolve_roster", "select_m1_slice", "write_m0_report"):
        assert (repo / "scripts" / f"{stem}.py").exists(), stem


def test_reports_run_after_the_data_stages():
    assert CHAIN.index("fetch_observations.py") < CHAIN.index("joint_coverage.py")
    assert CHAIN.index("joint_coverage.py") < CHAIN.index("write_m0_report.py")


def test_no_quota_spending_stage_is_in_the_convenience_script():
    """Burying a paid stage in a convenience script is how an unattended run
    empties a quota window."""
    from pathlib import Path as _P
    repo = _P(__file__).resolve().parent.parent
    # Derived, for the same reason as above: a pinned list of six would not
    # have caught plan v4's score_pairings.py if it were ever added to the chain.
    for script in sorted((repo / "scripts").glob("*.py")):
        if "SPENDS MODEL QUOTA" not in script.read_text():
            continue
        assert script.name not in CHAIN, (
            f"{script.stem} spends model quota and must not run from run_chain.sh"
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


def _prose_chain_order() -> list[str]:
    """The stage names from AGENTS.md's 'run the whole chain in this order'."""
    text = (REPO / "AGENTS.md").read_text()
    start = text.index("changing any source:")
    para = text[start:text.index("\n\n", start)]
    return [m for m in re.findall(r"`([a-z_0-9]+)`", para)]


def test_the_prose_chain_order_matches_the_script():
    """AGENTS.md states the order in prose and run_chain.sh encodes it.

    The script's own header says an order written in two places drifts, and it
    then did: verify_observations.py was added to the script after the merge
    and to the prose after verify_trap, in the same edit. Only stages the
    script actually runs are compared, because the prose also lists the
    quota-spending stages, which are deliberately not in the script.
    """
    in_script = [s for s in _prose_chain_order() if f"{s}.py" in CHAIN]
    positions = [CHAIN.index(f"{s}.py") for s in in_script]
    assert positions == sorted(positions), (
        "AGENTS.md lists these stages in an order run_chain.sh does not use: "
        f"{in_script}"
    )


def test_the_prose_chain_names_real_scripts():
    """A renamed script leaves its old name in the prose, pointing at nothing."""
    missing = [s for s in _prose_chain_order()
               if not (REPO / "scripts" / f"{s}.py").exists()]
    assert missing == [], f"AGENTS.md names scripts that do not exist: {missing}"
