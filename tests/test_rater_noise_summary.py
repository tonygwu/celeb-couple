"""The least significant difference must not be pooled across evidence shapes.

Measured 2026-09-14. `measure_rater_noise.py` repeated two dossiers four times
each:

    Michelle Pfeiffer 1995, ranked  -> 86, 86, 88, 86   SD 0.866
    Brad Pitt 1995, award           -> 92, 92, 92, 92   SD 0.0

and published one pooled figure: mean SD 0.433, LSD 1.2. That LSD was then used
to judge gaps between people whose estimates are rank-shaped -- the shape with
ALL of the measured variance. Pooling in a zero-variance shape halved the
number and made the noise floor look half as high as it is for exactly the
estimates it was applied to.

An independent check agrees. `cross_run_stability.py` compares two scoring runs
on byte-identical dossiers under the same contract id: the award-shaped
person-period returned the same estimate, and both rank-shaped ones moved by
2.0 points. That is inconsistent with an LSD of 1.2 and consistent with ~2.4.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "measure_rater_noise", REPO / "scripts/measure_rater_noise.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


#: The real measurement, verbatim from data/pilot/run/rater_noise.json.
TARGETS = [
    {"person": "Michelle Pfeiffer", "period": "1995", "shape": "ranked",
     "runs": {"fable": [86.0, 86.0, 88.0, 86.0]},
     "per_judge_sd": {"fable": 0.8660254037844386}},
    {"person": "Brad Pitt", "period": "1995", "shape": "award",
     "runs": {"fable": [92.0, 92.0, 92.0, 92.0]},
     "per_judge_sd": {"fable": 0.0}},
]


def test_the_ranked_lsd_is_about_twice_the_pooled_one():
    h = _mod().summarise(TARGETS, ["fable"])
    ranked = h["by_shape"]["ranked"]["least_significant_difference_95pct"]
    assert 2.3 <= ranked <= 2.5, (
        f"ranked LSD {ranked}; 2.77 * 0.866 is about 2.4, and the pooled "
        "figure of 1.2 is what this test exists to stop being published"
    )


def test_the_pooled_figure_is_still_reported_but_named_as_pooled():
    h = _mod().summarise(TARGETS, ["fable"])
    assert h["mean_within_judge_sd"] == 0.433
    assert "pooled" in h["caveat"].lower()


def test_four_identical_draws_are_not_reported_as_zero_noise():
    """Four identical draws from a low-variance process look exactly like four
    draws from a zero-variance one. Reporting SD 0.0 as a finding is the
    'accept-and-guess' failure: a sample too small to see the variance becomes
    a claim that there is none."""
    h = _mod().summarise(TARGETS, ["fable"])
    assert "award" in h["shapes_with_degenerate_sample"], (
        "a shape whose every repeat returned the same value must be flagged, "
        "not published as an LSD of 0.0"
    )
    assert h["by_shape"]["award"]["least_significant_difference_95pct"] is None


def test_a_shape_that_really_varies_is_not_flagged_as_degenerate():
    h = _mod().summarise(TARGETS, ["fable"])
    assert "ranked" not in h["shapes_with_degenerate_sample"]


def test_an_empty_measurement_reports_nothing_rather_than_zero():
    h = _mod().summarise([], ["fable"])
    assert h["mean_within_judge_sd"] is None
    assert h["least_significant_difference_95pct"] is None
    assert h["by_shape"] == {}


def test_a_missing_judge_is_still_named():
    h = _mod().summarise(TARGETS, ["fable", "astra"])
    assert h["judges_with_no_runs"] == ["astra"]
    assert h["single_judge"] is True
    assert "astra" in h["caveat"]


def test_the_committed_artifact_carries_the_per_shape_breakdown():
    """Optional: needs the artifact, which lives under a gitignored data/."""
    import json
    f = REPO / "data/pilot/run/rater_noise.json"
    if not f.exists():
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")
    h = json.loads(f.read_text())["headline"]
    assert "by_shape" in h, "re-run: measure_rater_noise.py --recompute"


# --------------------------------------------------------------------------
# Clobber protection across BOTH dimensions of the measurement
# --------------------------------------------------------------------------

def test_a_smaller_target_set_cannot_replace_a_larger_one(tmp_path):
    """`guard_output` was given `repeats` as its quality field, when repeats was
    the only thing that varied. Making the target count a flag added a second
    dimension the guard could not see: `--ranked 1 --award 1 --repeats 4` has
    the same repeats as a six-target run and would have replaced it, turning a
    24-call measurement into an 8-call one with no warning.

    The guarded field is now total_runs = targets x repeats x judges, which is
    still ONE explicit field and covers both dimensions.
    """
    import json
    from packages.llmkit.outputs import ClobberRefused, guard_output

    p = tmp_path / "rater_noise.json"
    p.write_text(json.dumps({"repeats": 4, "total_runs": 24, "targets": [1] * 6}))

    with pytest.raises(ClobberRefused):
        guard_output(p, field="total_runs", value=8)


def test_an_equal_or_richer_measurement_is_still_allowed(tmp_path):
    import json
    from packages.llmkit.outputs import guard_output

    p = tmp_path / "rater_noise.json"
    p.write_text(json.dumps({"repeats": 4, "total_runs": 24}))
    guard_output(p, field="total_runs", value=24)     # a re-run
    guard_output(p, field="total_runs", value=48)     # a wider run


def test_the_committed_artifact_records_its_total_runs():
    """Optional: needs the artifact."""
    import json
    f = REPO / "data/pilot/run/rater_noise.json"
    if not f.exists():
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")
    blob = json.loads(f.read_text())
    assert "total_runs" in blob, "re-run measure_rater_noise.py --recompute"
    judges = {j for t in blob["targets"] for j in t["runs"]}
    assert blob["total_runs"] == len(blob["targets"]) * blob["repeats"] * len(judges)


def test_the_sd_is_the_sample_standard_deviation():
    """`pstdev` treats the four runs as the whole population of the rating
    process. They are a SAMPLE of it, and the population formula underestimates
    the population SD by sqrt((n-1)/n) — about 13% at n = 4.

    The rank-shaped LSD went 1.2 (pooled across shapes) -> 2.22 (per shape,
    pstdev) -> 2.56 (per shape, sample SD). Every conclusion in the report held
    at all three, which is the reassuring part; the number being right is the
    point.
    """
    import statistics
    runs = [86.0, 86.0, 88.0, 88.0]
    assert statistics.pstdev(runs) == 1.0
    assert round(statistics.stdev(runs), 3) == 1.155
    src = (REPO / "scripts/measure_rater_noise.py").read_text()
    assert "statistics.pstdev" not in src, (
        "the population SD underestimates a sampled process"
    )


def test_recompute_rebuilds_the_sds_from_the_runs():
    """`--recompute` reused the STORED per_judge_sd, so a corrected estimator
    could not be applied by replay. "Reproducibility comes from replaying
    stored responses" has to mean recomputing from them."""
    src = (REPO / "scripts/measure_rater_noise.py").read_text()
    recompute = src[src.index("if args.recompute"):]
    assert 'row["per_judge_sd"]' in recompute, (
        "the replay path must recompute the SDs from the stored runs"
    )


def test_no_verdict_flips_across_the_leave_one_out_range():
    """The noise floor gates every significance claim in the report and rests
    on four dossiers. If dropping one moved it far enough to flip a verdict,
    the verdict would be a property of that dossier.

    Measured: the floor moves between 2.35 and 2.89. The two 2.0-point results
    — order sensitivity, and the cross-run moves — are the closest to the edge
    and stay inside even at 2.35. S2's 4-point spread stays outside even at
    2.89.
    """
    import json
    f = REPO / "data/pilot/run/rater_noise.json"
    stress = REPO / "data/pilot/stress/stress_report.json"
    if not (f.exists() and stress.exists()):
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")

    loo = (json.loads(f.read_text())["headline"].get("leave_one_out") or {}).get("ranked")
    assert loo, "the leave-one-out range must be recorded"
    lo, hi = loo["min"], loo["max"]

    findings = json.loads(stress.read_text())["findings"]
    for case, spread in ((k, v.get("spread")) for k, v in findings.items()):
        if spread is None:
            continue
        # A verdict is safe only if the spread is on the same side of the floor
        # at BOTH ends of the leave-one-out range.
        assert (spread <= lo) == (spread <= hi), (
            f"{case} spread {spread} flips across the leave-one-out range "
            f"[{lo}, {hi}] — that verdict depends on which dossiers were "
            f"repeated, not on the case")


def test_the_leave_one_out_range_is_reported_for_a_shape_that_has_a_floor():
    import json
    f = REPO / "data/pilot/run/rater_noise.json"
    if not f.exists():
        pytest.skip("data/ is gitignored")
    h = json.loads(f.read_text())["headline"]
    loo = h.get("leave_one_out") or {}
    assert "award" not in loo, (
        "the award shape has no measured floor; a leave-one-out on zeros says "
        "nothing and would look like a result"
    )


def _current_standing_contract_id() -> str:
    """The id the standing rubric on disk produces right now.

    Derived rather than pinned: a pinned id would need editing at every rubric
    bump, and forgetting would fail this test for a reason unrelated to what it
    tests.
    """
    import sys as _s
    from pathlib import Path as _P
    repo = _P(__file__).resolve().parent.parent
    _s.path.insert(0, str(repo))
    from packages.ids.keys import contract_id
    return contract_id((repo / "rubrics/standing/RUBRIC.md").read_bytes(),
                       (repo / "rubrics/standing/estimate.schema.json").read_bytes())


def test_recompute_runs_end_to_end_without_spending_a_call(tmp_path):
    """`--recompute` is the project's stated reproducibility mechanism —
    "reproducibility comes from replaying stored responses" — and it corrected
    the published noise floor twice tonight at no quota cost.

    It was covered only by a grep of its own source, which would pass on code
    that could not run. This executes it as a subprocess against a synthetic
    artifact, with CELEB_ACCOUNT unset, so a path that tried to reach a model
    would fail rather than quietly succeed.
    """
    import json
    import subprocess
    import sys as _sys
    from pathlib import Path as _P

    repo = _P(__file__).resolve().parent.parent
    art = tmp_path / "noise.json"
    art.write_text(json.dumps({
        # A CURRENT contract id, not a placeholder. `--recompute` now refuses
        # an artifact whose rubric is gone, and a fixture stamped "test" would
        # be refused -- which would make this test assert that the guard works
        # rather than that recompute does.
        "contract": {"contract_id": _current_standing_contract_id()},
        "repeats": 4,
        "headline": {"stale": "this must be replaced"},
        "targets": [
            {"person": "A", "period": "2000", "shape": "ranked",
             "runs": {"fable": [80.0, 80.0, 82.0, 82.0]},
             "per_judge_sd": {"fable": 999.0}},      # deliberately wrong
            {"person": "B", "period": "2000", "shape": "award",
             "runs": {"fable": [92.0, 92.0, 92.0, 92.0]},
             "per_judge_sd": {"fable": 999.0}},
        ],
    }))

    env = {"PATH": "/usr/bin:/bin", "HOME": str(_P.home())}
    r = subprocess.run(
        [_sys.executable, str(repo / "scripts/measure_rater_noise.py"),
         "--recompute", str(art)],
        capture_output=True, text=True, cwd=repo, env=env, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no model calls" in r.stdout

    out = json.loads(art.read_text())
    assert out["headline"].get("recomputed_from_stored_runs") is True
    assert "stale" not in out["headline"], "the old headline must be replaced"

    # The stored 999.0 must have been discarded and the SD rebuilt from runs.
    import statistics
    expected = statistics.stdev([80.0, 80.0, 82.0, 82.0])
    assert out["targets"][0]["per_judge_sd"]["fable"] == expected
    assert round(out["headline"]["by_shape"]["ranked"]["mean_within_judge_sd"],
                 3) == round(expected, 3)
    assert out["headline"]["by_shape"]["award"][
        "least_significant_difference_95pct"] is None
