from __future__ import annotations

from fractions import Fraction as F

import pytest

from modules.analytics.metrics import Pairing, PeriodExposure, as_estimate, partner_war
from modules.analytics.baseline import (
    CURRENT_RELEASE, BaselineChangeError, MetricRelease, cohort_median_partner,
    count_like_diagnostic,
)


def _k(pid, partner, w=F(1), period="2016"):
    return Pairing(pid, "a", "b", "on_screen",
                   (PeriodExposure(period, F(1), as_estimate(80.0),
                                   as_estimate(partner), "se_f", "se_p"),), w)


def test_the_baseline_cannot_be_edited_inside_its_own_version():
    with pytest.raises(BaselineChangeError, match="requires a NEW methodology version"):
        CURRENT_RELEASE.with_baseline(
            F(90), version=CURRENT_RELEASE.version, derivation="nudged it")


def test_changing_the_baseline_produces_a_new_named_version():
    nxt = CURRENT_RELEASE.with_baseline(
        F(90), version="metric-release-0.2", derivation="derived from a real corpus")
    assert nxt.version != CURRENT_RELEASE.version
    assert nxt.baseline == 90
    assert CURRENT_RELEASE.baseline == 85, "the old release is untouched"


def test_the_provisional_baseline_declares_that_it_is_a_placeholder():
    assert "PLACEHOLDER" in CURRENT_RELEASE.baseline_derivation
    assert "provisional" in CURRENT_RELEASE.version


def test_adding_unrelated_people_does_not_change_an_existing_score():
    mine = [_k("k1", 90.0), _k("k2", 88.0, period="2017")]
    before = partner_war(mine, CURRENT_RELEASE.baseline)
    _unrelated = [_k("x1", 99.0), _k("x2", 10.0)]
    assert partner_war(mine, CURRENT_RELEASE.baseline) == before


def test_monthly_representation_changes_neither_the_baseline_nor_the_total():
    annual = [_k("k", 90.0)]
    monthly = [Pairing("k", "a", "b", "on_screen", tuple(
        PeriodExposure(f"2016-{m:02d}", F(1, 12), as_estimate(80.0),
                       as_estimate(90.0), "se_f", "se_p") for m in range(1, 13)), F(1))]
    B = CURRENT_RELEASE.baseline
    assert partner_war(annual, B) == partner_war(monthly, B)
    assert cohort_median_partner(annual) == cohort_median_partner(monthly) == 90.0


def test_the_cohort_median_is_descriptive_and_is_not_the_live_baseline():
    ks = [_k("k1", 70.0), _k("k2", 90.0, period="2017"), _k("k3", 80.0, period="2018")]
    assert cohort_median_partner(ks) == 80.0
    assert CURRENT_RELEASE.baseline == 85, (
        "the frozen baseline must not track the cohort median, or every total "
        "would depend on who else happened to be scored"
    )


def test_the_count_like_diagnostic_reports_and_does_not_gate_without_a_threshold():
    per_person = {
        f"p{i}": [_k(f"k{i}_{j}", 90.0, period=str(2010 + j)) for j in range(i + 1)]
        for i in range(4)
    }
    d = count_like_diagnostic(per_person)
    assert d.threshold is None
    assert d.gates is False and d.disclosure_required is False
    assert "does not gate" in d.reading
    assert d.contribution_sd is not None


def test_identical_partner_estimates_make_partner_war_a_disguised_count():
    """Every partner at the same value, so Partner_WAR is exposure times a constant."""
    per_person = {
        f"p{i}": [_k(f"k{i}_{j}", 92.0, period=str(2010 + j)) for j in range(i + 1)]
        for i in range(5)
    }
    release = MetricRelease("test-1.0", F(85), "test", count_like_sd_threshold_points=1.0)
    d = count_like_diagnostic(per_person, release)
    assert d.contribution_sd == 0.0, "identical partners give identical per-unit value"
    assert d.disclosure_required is True
    assert "count of recognized pairings" in d.reading


def test_varied_partner_estimates_break_the_count_like_signature():
    per_person = {
        "p0": [_k("a", 60.0)],
        "p1": [_k("b", 99.0), _k("c", 61.0, period="2011")],
        "p2": [_k("d", 95.0), _k("e", 62.0, period="2012"), _k("f", 97.0, period="2013")],
        "p3": [_k("g", 63.0), _k("h", 98.0, period="2014")],
    }
    release = MetricRelease("test-1.0", F(85), "test", count_like_sd_threshold_points=1.0)
    d = count_like_diagnostic(per_person, release)
    assert d.contribution_sd is not None and d.contribution_sd > 1.0
    assert d.disclosure_required is False
    # R-squared would have fired here: it is near 1 on healthy data, which is
    # why it is context and not the decision.
    assert d.r_squared is not None and d.r_squared > 0.9


def test_too_few_people_reports_rather_than_inventing_an_r_squared():
    d = count_like_diagnostic({"p0": [_k("a", 90.0)]})
    assert d.contribution_sd is None and "too few" in d.reading
