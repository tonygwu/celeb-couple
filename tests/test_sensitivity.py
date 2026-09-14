"""Shared draws, and what the interval is allowed to claim."""

from __future__ import annotations

from fractions import Fraction as F

from modules.analytics.metrics import Pairing, PeriodExposure, as_estimate, gap
from modules.analytics.sensitivity import EstimateSpec, simulate


def _exp(period, q, f, p, fid, pid, days=None):
    return PeriodExposure(period, q, as_estimate(f), as_estimate(p), fid, pid, days)


def _pair(pid, a, b, periods, w=F(1)):
    return Pairing(pid, a, b, "on_screen", tuple(periods), w)


SPECS = {
    "se_a": EstimateSpec("se_a", 80.0, 3.0, publisher="P1"),
    "se_b": EstimateSpec("se_b", 90.0, 3.0, publisher="P2"),
    "se_c": EstimateSpec("se_c", 70.0, 3.0, publisher="P1"),
}


def test_mirrored_gaps_stay_exact_negatives_in_every_draw():
    ks = [_pair("k1", "a", "b", [_exp("2016", F(1), 80.0, 90.0, "se_a", "se_b")])]
    r = simulate(ks, SPECS, draws=200, check_mirror=True)
    assert r.mirror_checked is True


def test_one_estimate_reused_across_periods_moves_as_one_thing():
    """se_a serves 2015, 2016 and 2017 after nearby-period reuse."""
    shared = _pair("k_shared", "a", "b", [
        _exp("2015", F(1, 3), 80.0, 90.0, "se_a", "se_b"),
        _exp("2016", F(1, 3), 80.0, 90.0, "se_a", "se_b"),
        _exp("2017", F(1, 3), 80.0, 90.0, "se_a", "se_b"),
    ])
    # separate ids for the same values: three independent draws instead of one
    specs_split = dict(SPECS)
    for n in ("se_a1", "se_a2", "se_a3", "se_b1", "se_b2", "se_b3"):
        specs_split[n] = EstimateSpec(n, 80.0 if n.startswith("se_a") else 90.0, 3.0)
    split = _pair("k_split", "a", "b", [
        _exp("2015", F(1, 3), 80.0, 90.0, "se_a1", "se_b1"),
        _exp("2016", F(1, 3), 80.0, 90.0, "se_a2", "se_b2"),
        _exp("2017", F(1, 3), 80.0, 90.0, "se_a3", "se_b3"),
    ])
    r_shared = simulate([shared], SPECS, draws=3000, seed=1)
    r_split = simulate([split], specs_split, draws=3000, seed=1)
    width_shared = r_shared.total_high - r_shared.total_low
    width_split = r_split.total_high - r_split.total_low
    assert width_shared > width_split * 1.3, (
        "independent draws average out and fabricate precision; the shared draw "
        f"must give the WIDER interval (shared {width_shared:.2f} vs split "
        f"{width_split:.2f})"
    )


def test_the_point_estimate_is_not_moved_by_the_simulation():
    ks = [_pair("k1", "a", "b", [_exp("2016", F(1), 80.0, 90.0, "se_a", "se_b")])]
    r = simulate(ks, SPECS, draws=500)
    assert r.point_total == float(gap(ks[0])) == 10.0


def test_the_interval_brackets_the_point_estimate():
    ks = [_pair("k1", "a", "b", [_exp("2016", F(1), 80.0, 90.0, "se_a", "se_b")])]
    r = simulate(ks, SPECS, draws=4000)
    assert r.total_low < r.point_total < r.total_high


def test_a_seeded_run_is_reproducible():
    ks = [_pair("k1", "a", "b", [_exp("2016", F(1), 80.0, 90.0, "se_a", "se_b")])]
    a = simulate(ks, SPECS, draws=1000, seed=7)
    b = simulate(ks, SPECS, draws=1000, seed=7)
    assert (a.total_low, a.total_high) == (b.total_low, b.total_high)


def test_zero_spread_collapses_the_interval_onto_the_point():
    flat = {k: EstimateSpec(k, v.value, 0.0) for k, v in SPECS.items()}
    ks = [_pair("k1", "a", "b", [_exp("2016", F(1), 80.0, 90.0, "se_a", "se_b")])]
    r = simulate(ks, flat, draws=500)
    assert r.total_low == r.total_high == r.point_total


def test_a_shared_publisher_effect_widens_a_same_publisher_pairing():
    """Two estimates from one magazine do not have independent errors."""
    same = [_pair("k", "a", "c", [_exp("2016", F(1), 80.0, 70.0, "se_a", "se_c")])]
    no_pub = simulate(same, SPECS, draws=4000, seed=3, publisher_sd=0.0)
    with_pub = simulate(same, SPECS, draws=4000, seed=3, publisher_sd=6.0)
    # se_a and se_c share publisher P1, so a common shift cancels in their gap
    assert (with_pub.total_high - with_pub.total_low) <= (
        no_pub.total_high - no_pub.total_low) * 1.05


def test_the_result_says_what_it_is_not():
    ks = [_pair("k1", "a", "b", [_exp("2016", F(1), 80.0, 90.0, "se_a", "se_b")])]
    d = simulate(ks, SPECS, draws=200).as_dict()
    assert d["type"] == "sensitivity"
    assert "not a calibrated confidence interval" in d["not_a_confidence_interval"]
    assert "missing relationships" in d["assumptions"]["not_quantified"]
    assert "publisher selection bias" in d["assumptions"]["not_quantified"]


def test_an_unscored_pairing_contributes_nothing_under_perturbation():
    ks = [_pair("k_miss", "a", "b", [_exp("2016", F(1), 80.0, None, "se_a", None)])]
    r = simulate(ks, SPECS, draws=300)
    assert r.point_total == 0.0
    assert r.total_low == r.total_high == 0.0, "no evidence, so nothing to perturb"


# -- a missing spec must not read as certainty -------------------------------

def test_an_estimate_with_no_spec_is_refused():
    """Measured: _redraw fell back to the ORIGINAL value for any estimate id
    with no spec, so a forgotten spec silently narrowed the interval and an
    empty spec map produced a ZERO-WIDTH one:

        both specs     interval width 16.679
        se_b MISSING   interval width 11.544
        no specs       interval width  0.000

    A zero-width sensitivity interval reads as "this total is certain". That is
    the exact accept-and-guess failure: a missing input became a confident
    answer with nothing raised.

    An estimate that genuinely should not move is expressed by a spec with
    sd=0.0, so the choice is visible in the caller.
    """
    import pytest
    ks = [_pair("k", "a", "b", [_exp("2016", F(1), 70.0, 85.0, "se_a", "se_b")])]
    with pytest.raises(ValueError, match="se_b"):
        simulate(ks, {"se_a": EstimateSpec("se_a", 70.0, 3.0)}, draws=10)


def test_an_empty_spec_map_is_refused_rather_than_returning_zero_width():
    import pytest
    ks = [_pair("k", "a", "b", [_exp("2016", F(1), 70.0, 85.0, "se_a", "se_b")])]
    with pytest.raises(ValueError):
        simulate(ks, {}, draws=10)


def test_an_explicit_zero_sd_is_allowed():
    """Not moving is a legitimate choice. It just has to be stated."""
    ks = [_pair("k", "a", "b", [_exp("2016", F(1), 70.0, 85.0, "se_a", "se_b")])]
    r = simulate(ks, {"se_a": EstimateSpec("se_a", 70.0, 0.0),
                      "se_b": EstimateSpec("se_b", 85.0, 0.0)}, draws=50)
    assert r.total_high - r.total_low == 0.0


def test_an_unscored_period_needs_no_spec():
    """A period with no estimate on either side references no estimate id, so
    there is nothing to require a spec for."""
    ks = [_pair("k", "a", "b", [_exp("2016", F(1, 2), 70.0, 85.0, "se_a", "se_b"),
                                _exp("2017", F(1, 2), None, None, None, None)])]
    r = simulate(ks, {"se_a": EstimateSpec("se_a", 70.0, 2.0),
                      "se_b": EstimateSpec("se_b", 85.0, 2.0)}, draws=50)
    assert r.total_high > r.total_low


def test_the_error_names_every_missing_estimate_not_just_the_first():
    import pytest
    ks = [_pair("k", "a", "b", [_exp("2016", F(1), 70.0, 85.0, "se_a", "se_b")])]
    with pytest.raises(ValueError) as e:
        simulate(ks, {}, draws=10)
    assert "se_a" in str(e.value) and "se_b" in str(e.value), (
        "naming one at a time turns a two-line fix into two runs"
    )


# -- clamping at the scale boundary ------------------------------------------

def test_clamping_at_the_ceiling_is_reported():
    """Draws are clamped to 0-100. A clamp is not a draw: it puts a point mass
    on the boundary and compresses the interval on that side.

    This matters for exactly the estimates the project cares about. An award
    estimate of 94 with a 5-point support band has about 11.5% of its draws
    above 100, so the upward uncertainty on the highest estimates — the ones
    every comparable pairing is made of — is the most understated.

    Reported rather than corrected: the scale really is bounded at 100, and a
    truncated normal would be a different declared assumption, not a bug fix.
    """
    ks = [_pair("k", "a", "b", [_exp("2016", F(1), 94.0, 94.0, "se_a", "se_b")])]
    specs = {"se_a": EstimateSpec("se_a", 94.0, 5.0),
             "se_b": EstimateSpec("se_b", 94.0, 5.0)}
    r = simulate(ks, specs, draws=4000, seed=3)
    assert r.clamped_share > 0.05, r.clamped_share
    assert "clamped_share" in r.assumptions["scale_clamping"]


def test_estimates_far_from_the_boundary_clamp_nothing():
    ks = [_pair("k", "a", "b", [_exp("2016", F(1), 70.0, 60.0, "se_a", "se_b")])]
    specs = {"se_a": EstimateSpec("se_a", 70.0, 3.0),
             "se_b": EstimateSpec("se_b", 60.0, 3.0)}
    assert simulate(ks, specs, draws=2000, seed=3).clamped_share == 0.0


def test_the_clamping_assumption_travels_with_the_result():
    """The module's header promises the assumption set travels with every
    result. A bounded scale is an assumption."""
    ks = [_pair("k", "a", "b", [_exp("2016", F(1), 80.0, 80.0, "se_a", "se_b")])]
    specs = {"se_a": EstimateSpec("se_a", 80.0, 2.0),
             "se_b": EstimateSpec("se_b", 80.0, 2.0)}
    assert "scale_clamping" in simulate(ks, specs, draws=100).assumptions
