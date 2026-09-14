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
