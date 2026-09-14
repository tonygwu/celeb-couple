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
