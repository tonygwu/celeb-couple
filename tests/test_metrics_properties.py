"""Property-based tests for the metric invariants.

The example-based tests in test_metrics.py pin specific worked numbers. These
assert the invariants hold for ARBITRARY inputs, which is what catches the case
nobody thought to write down.
"""

from __future__ import annotations

from fractions import Fraction as F

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from modules.analytics.metrics import (
    Pairing, PeriodExposure, as_estimate, covered_share, gap, partner_war,
    paw_rate, paw_total, scored_exposure, scored_weight,
)

# Estimates are on a 0-100 scale and reach the page with one decimal.
estimates = st.decimals(min_value=0, max_value=100, places=1).map(lambda d: F(str(d)))
weights = st.integers(min_value=1, max_value=5).map(F)
periods = st.integers(min_value=1950, max_value=2026).map(str)


@st.composite
def exposure(draw, force_scored: bool = False):
    f = draw(estimates)
    p = draw(estimates)
    if not force_scored:
        f = draw(st.one_of(st.none(), st.just(f)))
        p = draw(st.one_of(st.none(), st.just(p)))
    return PeriodExposure(draw(periods), F(1), f, p, "se_f", "se_p")


@st.composite
def pairing(draw, force_scored: bool = False):
    n = draw(st.integers(min_value=1, max_value=4))
    raw = [draw(exposure(force_scored)) for _ in range(n)]
    share = F(1, n)
    parts = tuple(
        PeriodExposure(f"{e.period}-{i}", share, e.focal, e.partner,
                       e.focal_estimate_id, e.partner_estimate_id)
        for i, e in enumerate(raw)
    )
    return Pairing(f"k{draw(st.integers(0, 10**6))}", "a", "b",
                   draw(st.sampled_from(["on_screen", "real_life"])),
                   parts, draw(weights))


@given(pairing())
@settings(max_examples=300, deadline=None)
def test_gap_mirrors_exactly_for_any_pairing(k):
    g, gm = gap(k), gap(k.mirror())
    if g is None:
        assert gm is None
    else:
        assert g == -gm


@given(pairing())
@settings(max_examples=300, deadline=None)
def test_mirroring_twice_is_the_identity(k):
    assert gap(k.mirror().mirror()) == gap(k)
    assert covered_share(k.mirror().mirror()) == covered_share(k)


@given(st.lists(pairing(), min_size=1, max_size=6))
@settings(max_examples=200, deadline=None)
def test_mirrored_contributions_sum_to_zero_over_any_set(ks):
    total = F(0)
    for k in ks:
        for side in (k, k.mirror()):
            g = gap(side)
            if g is not None:
                total += scored_weight(side) * g
    assert total == 0


@given(st.lists(pairing(), min_size=1, max_size=6))
@settings(max_examples=200, deadline=None)
def test_totals_do_not_depend_on_the_order_of_pairings(ks):
    assert paw_total(ks) == paw_total(list(reversed(ks)))
    assert scored_exposure(ks) == scored_exposure(list(reversed(ks)))


@given(pairing(force_scored=True))
@settings(max_examples=200, deadline=None)
def test_a_fully_scored_pairing_has_covered_share_one(k):
    assert covered_share(k) == 1
    assert scored_weight(k) == k.w


@given(pairing())
@settings(max_examples=300, deadline=None)
def test_covered_share_never_exceeds_one_and_is_never_negative(k):
    assert 0 <= covered_share(k) <= 1


@given(st.lists(pairing(), min_size=1, max_size=5))
@settings(max_examples=200, deadline=None)
def test_rate_times_exposure_reconstructs_the_total(ks):
    r = paw_rate(ks)
    assume(r is not None)
    assert r * scored_exposure(ks) == paw_total(ks)


@given(pairing(force_scored=True), st.integers(2, 12))
@settings(max_examples=120, deadline=None)
def test_splitting_a_period_into_equal_parts_changes_nothing(k, parts):
    """The same evidence expressed at finer granularity must not move a number."""
    split = []
    for p in k.periods:
        share = p.q / parts
        for i in range(parts):
            split.append(PeriodExposure(f"{p.period}.{i}", share, p.focal, p.partner,
                                        p.focal_estimate_id, p.partner_estimate_id))
    finer = Pairing(k.pairing_id, k.focal_id, k.partner_id, k.domain,
                    tuple(split), k.w)
    assert covered_share(finer) == covered_share(k)
    assert gap(finer) == gap(k)
    assert paw_total([finer]) == paw_total([k])


@given(st.lists(pairing(), min_size=1, max_size=5), estimates)
@settings(max_examples=200, deadline=None)
def test_partner_war_is_partner_mass_minus_baseline_times_exposure(ks, baseline):
    mass = F(0)
    for k in ks:
        mass += k.w * sum((p.q * p.partner for p in k.scored_periods()), F(0))
    assert partner_war(ks, baseline) == mass - baseline * scored_exposure(ks)


@given(st.lists(pairing(), min_size=1, max_size=5), st.lists(pairing(), max_size=4))
@settings(max_examples=200, deadline=None)
def test_adding_other_peoples_pairings_never_changes_a_total(mine, theirs):
    before_total, before_rate = paw_total(mine), paw_rate(mine)
    _ = paw_total(mine + theirs)     # computing a combined board
    assert paw_total(mine) == before_total
    assert paw_rate(mine) == before_rate


@given(pairing())
@settings(max_examples=300, deadline=None)
def test_an_unscored_pairing_contributes_nothing_anywhere(k):
    assume(covered_share(k) == 0)
    assert gap(k) is None and gap(k.mirror()) is None
    assert scored_weight(k) == 0
    assert paw_total([k]) == 0
    assert paw_rate([k]) is None
    assert partner_war([k], F(85)) == 0
