from __future__ import annotations

from fractions import Fraction as F

from modules.analytics.metrics import Pairing, PeriodExposure, as_estimate
from modules.analytics.comparability import (
    COMPARABLE, MISMATCHED, MISMATCH_CAVEAT, UNKNOWN_SHAPE,
    classify_pairing, same_shape_view,
)


def _k(pid, f=80.0, p=90.0):
    return Pairing(pid, "a", "b", "real_life",
                   (PeriodExposure("2000", F(1), as_estimate(f), as_estimate(p),
                                   "se_a", "se_b"),), F(1))


def test_same_shape_is_comparable_and_carries_no_caveat():
    c = classify_pairing("k1", "ordered_rank", "ordered_rank")
    assert c.status == COMPARABLE and c.comparable is True and c.caveat is None


def test_award_against_rank_is_mismatched_and_carries_the_caveat():
    c = classify_pairing("k1", "editorial_award", "ordered_rank")
    assert c.status == MISMATCHED and c.comparable is False
    assert c.caveat == MISMATCH_CAVEAT
    assert "which publication covered whom" in c.caveat


def test_an_unknown_shape_is_not_silently_treated_as_comparable():
    for a, b in (("editorial_award", None), (None, "ordered_rank"), (None, None)):
        c = classify_pairing("k1", a, b)
        assert c.status == UNKNOWN_SHAPE and c.comparable is False


def test_the_same_shape_view_is_labelled_as_a_scenario_not_a_correction():
    v = same_shape_view([_k("k1")], {"k1": ("ordered_rank", "ordered_rank")})
    assert v["is_a_correction"] is False
    assert "different and narrower question" in v["explanation"]


def test_the_view_reports_both_totals_so_the_difference_is_inspectable():
    ks = [_k("k1", 80.0, 90.0), _k("k2", 70.0, 95.0)]
    shapes = {"k1": ("ordered_rank", "ordered_rank"),
              "k2": ("editorial_award", "ordered_rank")}
    v = same_shape_view(ks, shapes)
    assert v["comparable_pairings"] == 1 and v["mismatched_pairings"] == 1
    assert v["paw_total_all_scored"] == 35.0     # +10 and +25
    assert v["paw_total_comparable_only"] == 10.0
    assert v["paw_total_all_scored"] != v["paw_total_comparable_only"]


def test_dropping_mismatched_pairings_never_touches_the_main_total():
    ks = [_k("k1", 80.0, 90.0), _k("k2", 70.0, 95.0)]
    shapes = {"k1": ("ordered_rank", "ordered_rank"),
              "k2": ("editorial_award", "ordered_rank")}
    v = same_shape_view(ks, shapes)
    from modules.analytics.metrics import paw_total
    assert v["paw_total_all_scored"] == float(paw_total(ks)), (
        "the main board must be unaffected by the scenario"
    )


def test_a_pairing_with_no_coverage_is_not_counted_as_scored():
    empty = Pairing("k0", "a", "b", "real_life",
                    (PeriodExposure("2000", F(1), as_estimate(80.0), None,
                                    "se_a", None),), F(1))
    v = same_shape_view([empty], {"k0": ("ordered_rank", "ordered_rank")})
    assert v["scored_pairings"] == 0


def test_every_classification_is_reported_not_just_the_comparable_ones():
    ks = [_k("k1"), _k("k2"), _k("k3")]
    shapes = {"k1": ("ordered_rank", "ordered_rank"),
              "k2": ("editorial_award", "ordered_rank"),
              "k3": (None, "ordered_rank")}
    v = same_shape_view(ks, shapes)
    assert len(v["classifications"]) == 3
    assert {c["status"] for c in v["classifications"]} == {
        COMPARABLE, MISMATCHED, UNKNOWN_SHAPE}
