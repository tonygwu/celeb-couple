"""Invariants of the pairing metrics, as exact arithmetic."""

from __future__ import annotations

from fractions import Fraction as F

import pytest

from modules.analytics.metrics import (
    GAP_YEAR_DAYS,
    Pairing,
    PeriodExposure,
    apply_cross_gender_offset,
    as_estimate,
    covered_share,
    gap,
    gap_years,
    partner_war,
    paw_rate,
    paw_total,
    scored_exposure,
    scored_weight,
)


def _pair(pid, focal, partner, periods, w=F(1), domain="on_screen"):
    return Pairing(pid, focal, partner, domain, tuple(periods), w)


def _p(period, q, f, pa, days=None):
    return PeriodExposure(
        period, q, as_estimate(f), as_estimate(pa),
        f"se_{period}_f", f"se_{period}_p", days,
    )


# -- worked example E -------------------------------------------------------

TWO_YEAR = _pair(
    "k_E", "focal", "partner",
    [_p("2016", F(366, 731), 80.0, 90.0, 366), _p("2017", F(365, 731), 84.0, 88.0, 365)],
    domain="real_life",
)


def test_episode_weighted_gap_is_exactly_5120_over_731():
    assert gap(TWO_YEAR) == F(5120, 731)


def test_gap_years_is_exactly_5120_over_365_point_25():
    assert gap_years(TWO_YEAR) == F(5120) / GAP_YEAR_DAYS == F(20480, 1461)


def test_monthly_representation_changes_neither_number():
    """24 monthly rows are one copied yearly estimate, not 24 observations."""
    monthly = []
    for year, f, pa, ndays in [(2016, 80.0, 90.0, 366), (2017, 84.0, 88.0, 365)]:
        for m in range(1, 13):
            dm = [31, 29 if year == 2016 else 28, 31, 30, 31, 30,
                  31, 31, 30, 31, 30, 31][m - 1]
            monthly.append(
                PeriodExposure(
                    f"{year}-{m:02d}", F(dm, 731), as_estimate(f), as_estimate(pa),
                    f"se_{year}_f", f"se_{year}_p", dm,
                )
            )
    k = _pair("k_E_monthly", "focal", "partner", monthly, domain="real_life")
    assert covered_share(k) == 1
    assert gap(k) == gap(TWO_YEAR) == F(5120, 731)
    assert gap_years(k) == gap_years(TWO_YEAR)


def test_cancellation_reaches_exactly_zero_and_erases_no_record():
    """v2 used -10 against +7 and called the total zero. It was -3."""
    # the exact negative, built from the convention rather than typed as a decimal
    exact = PeriodExposure("2019", F(1), F(90), F(90) - F(5120, 731), "x", "y", 365)
    opposite = _pair("k_E2", "focal", "partner2", [exact], domain="real_life")
    both = [TWO_YEAR, opposite]
    assert gap(opposite) == -F(5120, 731)
    assert paw_total(both) == 0
    assert len(both) == 2, "both records still present"
    assert gap(TWO_YEAR) != 0 and gap(opposite) != 0


# -- mirroring ---------------------------------------------------------------

def test_gap_mirrors_exactly():
    assert gap(TWO_YEAR.mirror()) == -gap(TWO_YEAR)
    assert gap(TWO_YEAR.mirror().mirror()) == gap(TWO_YEAR)


def test_complete_graph_mirrored_contributions_sum_to_zero():
    ks = [
        _pair("k1", "a", "b", [_p("2016", F(1), 70.0, 85.0)]),
        _pair("k2", "a", "c", [_p("2018", F(1), 72.0, 61.5)]),
        _pair("k3", "b", "c", [_p("2020", F(1), 88.0, 64.25)], w=F(2)),
    ]
    total = F(0)
    for k in ks:
        total += scored_weight(k) * gap(k) + scored_weight(k.mirror()) * gap(k.mirror())
    assert total == 0


# -- missingness -------------------------------------------------------------

def test_one_unscored_side_removes_the_pairing_from_BOTH_views():
    k = _pair("k_miss", "ada", "col", [_p("2016", F(1), 78.0, None)])
    assert covered_share(k) == 0
    assert gap(k) is None
    assert gap(k.mirror()) is None
    assert scored_weight(k) == scored_weight(k.mirror()) == 0
    assert paw_total([k]) == paw_total([k.mirror()]) == 0


def test_partial_coverage_contributes_only_its_observed_mass():
    k = _pair(
        "k_part", "a", "b",
        [_p("2016", F(1, 2), 80.0, 90.0), _p("2017", F(1, 2), 80.0, None)],
    )
    assert covered_share(k) == F(1, 2)
    assert gap(k) == 10                      # the observed half, not renormalised away
    assert scored_weight(k) == F(1, 2)       # only half the exposure mass counts


def test_zero_coverage_never_divides_and_never_returns_zero():
    k = _pair("k_zero", "a", "b", [_p("2016", F(1), None, None)])
    assert gap(k) is None
    assert paw_rate([k]) is None, "no scored exposure means unscored, not a rate of 0"


# -- invariance --------------------------------------------------------------

def test_order_of_pairings_does_not_change_totals():
    ks = [
        _pair("k1", "a", "b", [_p("2016", F(1), 70.0, 85.0)]),
        _pair("k2", "a", "c", [_p("2018", F(1), 72.0, 61.5)]),
        _pair("k3", "a", "d", [_p("2020", F(1), 88.0, 64.25)]),
    ]
    assert paw_total(ks) == paw_total(list(reversed(ks)))
    assert paw_rate(ks) == paw_rate(list(reversed(ks)))


def test_repeat_costars_in_different_films_count_again():
    one = _pair("f1", "a", "b", [_p("2016", F(1), 70.0, 80.0)])
    two = _pair("f2", "a", "b", [_p("2019", F(1), 72.0, 82.0)])
    assert paw_total([one, two]) == paw_total([one]) + paw_total([two]) == 20


def test_a_longer_shoot_earns_no_extra_exposure():
    short = _pair("f_short", "a", "b", [_p("2016", F(1), 70.0, 80.0, 30)])
    long_ = _pair(
        "f_long", "a", "b",
        [_p("2016", F(1, 2), 70.0, 80.0, 200), _p("2017", F(1, 2), 70.0, 80.0, 200)],
    )
    assert scored_weight(short) == scored_weight(long_) == 1
    assert paw_total([short]) == paw_total([long_]) == 10


def test_adding_unrelated_people_does_not_change_an_existing_score():
    mine = [_pair("k1", "a", "b", [_p("2016", F(1), 70.0, 85.0)])]
    before_total, before_rate = paw_total(mine), paw_rate(mine)
    _unrelated = [_pair("k9", "x", "y", [_p("2016", F(1), 10.0, 99.0)])]
    assert paw_total(mine) == before_total
    assert paw_rate(mine) == before_rate


# -- Partner_WAR and the frozen baseline -------------------------------------

def test_partner_war_equals_partner_mass_minus_baseline_times_exposure():
    ks = [
        _pair("k1", "a", "b", [_p("2016", F(1), 70.0, 85.0)]),
        # Partial coverage is expressed by an UNSCORED period, not by shares
        # that fail to add up. q is a share of this pairing's exposure, so
        # omitting the uncovered half would make the shares sum to 1/2 and
        # `covered_share` would still read 1/2 -- the same answer by accident.
        # The pairing now says what it means: two half-year periods, one of
        # which has no estimate on either side.
        _pair("k2", "a", "c", [_p("2018", F(1, 2), 72.0, 91.0),
                               _p("2019", F(1, 2), None, None)]),
    ]
    B = F(80)
    mass = F(0)
    for k in ks:
        mass += k.w * sum((p.q * p.partner for p in k.scored_periods()), F(0))
    assert partner_war(ks, B) == mass - B * scored_exposure(ks)


def test_changing_the_baseline_moves_totals_at_rates_that_differ_by_exposure():
    """Exactly why B is frozen inside the metric release."""
    heavy = [_pair("k1", "a", "b", [_p("2016", F(1), 70.0, 85.0)]),
             _pair("k2", "a", "c", [_p("2018", F(1), 70.0, 85.0)])]
    light = [_pair("k3", "d", "e", [_p("2016", F(1), 70.0, 85.0)])]
    d_heavy = partner_war(heavy, F(80)) - partner_war(heavy, F(70))
    d_light = partner_war(light, F(80)) - partner_war(light, F(70))
    assert d_heavy == -10 * scored_exposure(heavy) == -20
    assert d_light == -10 * scored_exposure(light) == -10
    assert d_heavy != d_light, "a moving B is not a neutral relabelling"


def test_monthly_representation_does_not_change_partner_war():
    annual = [_pair("k", "a", "b", [_p("2016", F(1), 70.0, 85.0)])]
    monthly = [_pair("k", "a", "b", [
        PeriodExposure(f"2016-{m:02d}", F(1, 12), F(70), F(85), "sf", "sp")
        for m in range(1, 13)
    ])]
    assert partner_war(annual, F(80)) == partner_war(monthly, F(80))


# -- the cross-gender offset diagnostic --------------------------------------

def _career(pid, n_pairings, focal, partner):
    return [
        _pair(f"{pid}_{i}", pid, f"{pid}_partner_{i}", [_p(f"20{10+i}", F(1), focal, partner)])
        for i in range(n_pairings)
    ]


@pytest.mark.parametrize("delta", [F(-6), F(-4), F(-2), F(0), F(2), F(4), F(6)])
def test_offset_identity_paw_total_moves_by_delta_times_exposure(delta):
    ks = _career("p", 3, 70.0, 85.0)
    shifted = [apply_cross_gender_offset(k, delta) for k in ks]
    assert paw_total(shifted) - paw_total(ks) == delta * scored_exposure(ks)


@pytest.mark.parametrize("delta", [F(-6), F(-2), F(2), F(6)])
def test_offset_identity_paw_rate_moves_by_exactly_delta(delta):
    ks = _career("p", 3, 70.0, 85.0)
    shifted = [apply_cross_gender_offset(k, delta) for k in ks]
    assert paw_rate(shifted) - paw_rate(ks) == delta


@pytest.mark.parametrize("delta", [F(-6), F(-4), F(-2), F(2), F(4), F(6)])
def test_a_constant_offset_cannot_reorder_paw_rate_but_can_reorder_cumulative_paw(delta):
    """The prediction the diagnostic tests against itself."""
    people = {
        "few_strong": _career("few_strong", 1, 60.0, 90.0),   # rate +30, exposure 1
        "many_mild": _career("many_mild", 8, 70.0, 72.0),     # rate  +2, exposure 8
    }
    def ranks(by):
        return [n for n, _ in sorted(by.items(), key=lambda kv: -kv[1])]

    rate_before = ranks({n: paw_rate(ks) for n, ks in people.items()})
    total_before = ranks({n: paw_total(ks) for n, ks in people.items()})
    shifted = {n: [apply_cross_gender_offset(k, delta) for k in ks]
               for n, ks in people.items()}
    rate_after = ranks({n: paw_rate(ks) for n, ks in shifted.items()})
    total_after = ranks({n: paw_total(ks) for n, ks in shifted.items()})

    assert rate_after == rate_before, (
        "a constant offset shifts every rate by the same delta, so rate ranks "
        "within a view must not move; if they do, the implementation is wrong"
    )
    if delta >= F(4):
        assert total_after != total_before, (
            "cumulative PAW weights by exposure, so a large enough offset must "
            "be able to reorder it"
        )


def test_offset_reverses_sign_in_the_mirrored_view():
    ks = _career("p", 2, 70.0, 85.0)
    mirrored = [k.mirror() for k in ks]
    delta = F(5)
    up = paw_total([apply_cross_gender_offset(k, delta) for k in ks]) - paw_total(ks)
    # in the mirrored view the SAME people are now the focal side, so the same
    # constant applied to that side's partners moves the total the other way
    down = paw_total(mirrored) - paw_total(
        [apply_cross_gender_offset(k, delta).mirror() for k in ks]
    )
    assert up == down == delta * scored_exposure(ks)


# -- the temporal-share partition -------------------------------------------

def test_shares_that_do_not_partition_the_pairing_are_refused():
    """`q` is a SHARE of the pairing's exposure, so it sums to 1 by definition.
    Nothing checked it. A pairing whose shares summed to 1.5 would give
    covered_share 1.5 and scored_weight w*1.5, overweighting it silently in
    every total -- and covered_share is what MIN_JOINT_COVERAGE compares
    against, so an unqualified pairing could pass on arithmetic that cannot be
    right."""
    import pytest
    with pytest.raises(ValueError, match="sum to 3/2"):
        _pair("bad", "a", "b",
              [_p("2016", F(1), 70.0, 85.0), _p("2017", F(1, 2), 70.0, 85.0)])


def test_the_error_names_the_periods_and_their_shares():
    import pytest
    with pytest.raises(ValueError) as e:
        _pair("bad", "a", "b", [_p("2016", F(1, 3), 70.0, 85.0)])
    msg = str(e.value)
    assert "'bad'" in msg and "2016=1/3" in msg, (
        "an error that does not say which period is wrong leaves the reader "
        "to diff two fraction lists by hand"
    )


def test_a_pairing_with_no_eligible_periods_is_allowed():
    """No eligible period is a real state, reported as unscored, not an error."""
    k = _pair("empty", "a", "b", [])
    assert covered_share(k) == 0
    assert gap(k) is None


def test_partial_coverage_is_expressed_by_an_unscored_period():
    """The supported way to say "half of this pairing has no estimates": list
    the period with None on both sides. The shares still partition."""
    k = _pair("half", "a", "b",
              [_p("2016", F(1, 2), 70.0, 85.0), _p("2017", F(1, 2), None, None)])
    assert covered_share(k) == F(1, 2)
    assert gap(k) == F(15)


def test_mirroring_preserves_the_partition():
    k = _pair("k", "a", "b",
              [_p("2016", F(1, 2), 70.0, 85.0), _p("2017", F(1, 2), None, None)])
    m = k.mirror()
    assert sum((p.q for p in m.periods), F(0)) == 1
    assert gap(m) == -gap(k)
