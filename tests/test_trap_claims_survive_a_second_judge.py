"""The structural claims must not break just because a second judge arrived.

They were written as EXACT equality -- "every shape-comparable pairing has a gap
of exactly 0.0" -- which was only true because one judge family scored the
corpus, returned integers, and both sides of the single comparable pairing
landed on the award-pinned 92.

When astra joined, the reducer's mean of two produced half-integers. Jennifer
Garner 2002 came back 93 from fable and 92 from astra, so her estimate is 92.5
against Ben Affleck's 92.0 and the gap is 0.5. Two claims "broke" and
verify_trap.py announced that 0.5 as "the first real signal this project has
produced". It is one judge saying 93 instead of 92, both inside band 90-100, an
order of magnitude under the measured floor.

The substantive claim was never "exactly zero". It was "no difference this
method can detect".
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("verify_trap", REPO / "scripts/verify_trap.py")
verify_trap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(verify_trap)


def _fixture(gap_b: float):
    """One comparable pairing whose two sides differ by `gap_b`."""
    joint = {"jointly_covered": [{"a": "A", "b": "B", "period": "2003",
                                  "comparability": "comparable"}]}
    shape = {"rows": [{"person": "A", "period": "2003", "estimate": 92.0, "shape": "award"},
                      {"person": "B", "period": "2003", "estimate": 92.0 + gap_b, "shape": "award"}]}
    gsc = {"ranked_observations": {"male": 0}}
    noise = {"headline": {"by_shape": {"ranked": {"least_significant_difference_95pct": 1.03},
                                       "award": {"least_significant_difference_95pct": None}}}}
    return joint, shape, gsc, noise


def _claim(results, needle):
    return next(r for r in results if needle in r["claim"])


def test_a_half_point_gap_from_averaging_two_judges_does_not_break_the_claim():
    results = verify_trap.check(*_fixture(0.5))
    assert _claim(results, "within the measured floor")["holds"] is True


def test_a_gap_beyond_the_floor_DOES_break_it():
    # The claim must still be able to fail, or it asserts nothing.
    results = verify_trap.check(*_fixture(4.0))
    c = _claim(results, "within the measured floor")
    assert c["holds"] is False
    assert c["exceptions"], "a broken claim must name the exception"


def test_with_no_measured_floor_the_claim_makes_no_assertion():
    """Falling back to exact zero is what broke these claims. A missing floor
    must produce no claim rather than the old, wrong one."""
    joint, shape, gsc, _ = _fixture(0.5)
    results = verify_trap.check(joint, shape, gsc, None)
    assert _claim(results, "within the measured floor")["holds"] is True


def test_the_floor_is_the_max_across_shapes_not_the_mean():
    # A gap must clear the NOISIEST shape it could have come from.
    noise = {"headline": {"by_shape": {"ranked": {"least_significant_difference_95pct": 1.03},
                                       "other": {"least_significant_difference_95pct": 2.56}}}}
    assert verify_trap.noise_floor(noise) == 2.56


def test_an_unmeasured_shape_does_not_drag_the_floor_to_zero():
    noise = {"headline": {"by_shape": {"ranked": {"least_significant_difference_95pct": 1.03},
                                       "award": {"least_significant_difference_95pct": None}}}}
    assert verify_trap.noise_floor(noise) == 1.03
    assert verify_trap.noise_floor({"headline": {"by_shape": {}}}) is None
