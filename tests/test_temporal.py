"""Dates keep their precision; exposure arithmetic stays exact.

Every case here maps to a line in the plan's test matrix.
"""

from __future__ import annotations

from datetime import date
from fractions import Fraction

import pytest

from packages.temporal.dates import (
    GAP_YEAR_DAYS,
    Censoring,
    Interval,
    Precision,
    PreciseDate,
    PrecisionError,
    from_wikidata,
)


# -- year precision never becomes January 1 -------------------------------

def test_wikidata_year_precision_does_not_become_january_first():
    """Probed 2026-09-13: Wikidata serves year precision as '1984-01-01', code 9."""
    d = from_wikidata("1984-01-01", 9, "c_0007")
    assert d.value == "1984"
    assert d.precision is Precision.YEAR
    assert d.earliest() == date(1984, 1, 1)
    assert d.latest() == date(1984, 12, 31)
    # The January 1st is not representable as the stored value.
    assert "01-01" not in d.value


def test_wikidata_month_and_day_precision_keep_their_components():
    m = from_wikidata("+2020-03-01T00:00:00Z", 10, "c_0031")
    assert (m.value, m.precision) == ("2020-03", Precision.MONTH)
    assert m.latest() == date(2020, 3, 31)
    dd = from_wikidata("+2005-06-29T00:00:00Z", 11, "c_0032")
    assert (dd.value, dd.precision) == ("2005-06-29", Precision.DAY)
    assert dd.earliest() == dd.latest() == date(2005, 6, 29)


def test_precision_coarser_than_year_is_refused_not_widened():
    with pytest.raises(PrecisionError):
        from_wikidata("1980-01-01", 8, "c_1")  # decade precision


def test_a_date_cannot_be_built_without_a_precision_or_a_source():
    with pytest.raises(PrecisionError):
        PreciseDate("2016", "year", "c_1")        # a bare string is not a Precision
    with pytest.raises(PrecisionError):
        PreciseDate("2016", Precision.YEAR, "")   # unsourced
    with pytest.raises(PrecisionError):
        PreciseDate("2016-05-06", Precision.YEAR, "c_1")  # shape contradicts precision


def test_calendar_is_validated_including_leap_years():
    PreciseDate("2016-02-29", Precision.DAY, "c_1")       # 2016 is a leap year
    with pytest.raises(ValueError):
        PreciseDate("2015-02-29", Precision.DAY, "c_1")   # 2015 is not
    assert PreciseDate("2015-02", Precision.MONTH, "c_1").latest() == date(2015, 2, 28)
    assert PreciseDate("2016-02", Precision.MONTH, "c_1").latest() == date(2016, 2, 29)


# -- exposure shares are exact -------------------------------------------

def _span(a: str, b: str) -> Interval:
    return Interval(
        PreciseDate(a, Precision.DAY, "c_1"),
        PreciseDate(b, Precision.DAY, "c_1"),
    )


def test_two_calendar_years_do_not_split_evenly_across_a_leap_year():
    """Plan worked example E. v2 claimed q = 0.5 per year. It is not."""
    iv = _span("2016-01-01", "2017-12-31")
    assert iv.days() == 731
    shares = iv.year_shares()
    assert shares == {2016: Fraction(366, 731), 2017: Fraction(365, 731)}
    assert sum(shares.values()) == 1


def test_worked_example_E_episode_gap_is_exactly_5120_over_731():
    iv = _span("2016-01-01", "2017-12-31")
    yearly_gap = {2016: Fraction(10), 2017: Fraction(4)}
    gap = sum(q * yearly_gap[y] for y, q in iv.year_shares().items())
    assert gap == Fraction(5120, 731)


def test_worked_example_E_gap_years_are_exactly_5120_over_365_25():
    iv = _span("2016-01-01", "2017-12-31")
    yearly_gap = {2016: Fraction(10), 2017: Fraction(4)}
    gap_years = sum(
        yearly_gap[y] * Fraction(n) / GAP_YEAR_DAYS for y, n in iv.year_days().items()
    )
    assert gap_years == Fraction(5120, 1) / GAP_YEAR_DAYS
    assert GAP_YEAR_DAYS == Fraction(1461, 4)  # 365.25 exactly, not a float


def test_shares_always_sum_to_one():
    for a, b in [
        ("2016-01-01", "2016-01-01"),
        ("1999-11-15", "2003-02-28"),
        ("2000-02-29", "2000-03-01"),
        ("1995-06-01", "2012-06-01"),
    ]:
        assert sum(_span(a, b).year_shares().values()) == 1


# -- adult-window clipping ------------------------------------------------

def test_relationship_crossing_an_eighteenth_birthday_contributes_only_the_adult_part():
    iv = _span("2003-01-01", "2005-12-31")
    adult = iv.clip(not_before=date(2004, 7, 1))
    assert adult is not None
    assert adult.first_day() == date(2004, 7, 1)
    assert adult.last_day() == date(2005, 12, 31)
    assert 2003 not in adult.year_shares()


def test_a_wholly_underage_interval_clips_to_nothing():
    iv = _span("2001-01-01", "2002-12-31")
    assert iv.clip(not_before=date(2004, 7, 1)) is None


# -- ongoing episodes -----------------------------------------------------

def test_ongoing_episode_ends_at_last_supported_active_not_the_run_date():
    iv = Interval(
        start=PreciseDate("2019-05", Precision.MONTH, "c_1"),
        end=None,
        censoring=Censoring.ONGOING,
        last_supported_active=PreciseDate("2021-08", Precision.MONTH, "c_2"),
    )
    assert iv.last_day() == date(2021, 8, 31)
    assert max(iv.year_shares()) == 2021, "an ongoing episode must not run to today"


def test_ongoing_episode_requires_last_supported_active():
    with pytest.raises(ValueError):
        Interval(
            PreciseDate("2019", Precision.YEAR, "c_1"), None, Censoring.ONGOING, None
        )


def test_closed_episode_must_not_be_given_ongoing_censoring():
    with pytest.raises(ValueError):
        Interval(
            PreciseDate("2019", Precision.YEAR, "c_1"),
            PreciseDate("2020", Precision.YEAR, "c_1"),
            Censoring.ONGOING,
            PreciseDate("2020", Precision.YEAR, "c_1"),
        )


def test_interval_that_ends_before_it_starts_is_refused():
    with pytest.raises(ValueError):
        _span("2016-01-01", "2015-01-01")


# -- clipped edges must cite the claim they came from ------------------------

def test_a_clipped_end_cites_the_end_claim_not_the_start_claim():
    """`clip()` built the clipped END date with `self.start.source_ref`.

    The module's own header says source_ref is required "so an unsourced date
    cannot enter a record by accident". A date carrying the WRONG source is
    worse than one carrying none: it looks sourced and traces to a claim that
    says nothing about it. In a project whose product is traceability, an
    adult-window clip attributed the relationship's END to the claim that
    established its START.
    """
    iv = Interval(
        PreciseDate("2000-01-01", Precision.DAY, "claim_START"),
        PreciseDate("2010-12-31", Precision.DAY, "claim_END"),
    )
    clipped = iv.clip(not_after=date(2005, 6, 30))
    assert clipped is not None
    assert clipped.end.value == "2005-06-30"
    assert "claim_END" in clipped.end.source_ref, clipped.end.source_ref
    assert "claim_START" not in clipped.end.source_ref


def test_a_clipped_start_still_cites_the_start_claim():
    iv = Interval(
        PreciseDate("2000-01-01", Precision.DAY, "claim_START"),
        PreciseDate("2010-12-31", Precision.DAY, "claim_END"),
    )
    clipped = iv.clip(not_before=date(2003, 4, 1))
    assert clipped.start.value == "2003-04-01"
    assert "claim_START" in clipped.start.source_ref


def test_clipping_an_ongoing_interval_cites_the_supported_active_claim():
    """An ongoing interval has no end claim. What closes it is
    last_supported_active, so that is what a clipped end derives from -- never
    the run date and never the start."""
    iv = Interval(
        PreciseDate("2000-01-01", Precision.DAY, "claim_START"),
        None, Censoring.ONGOING,
        PreciseDate("2012-12-31", Precision.DAY, "claim_ACTIVE"),
    )
    clipped = iv.clip(not_after=date(2005, 6, 30))
    assert clipped.end.value == "2005-06-30"
    assert "claim_ACTIVE" in clipped.end.source_ref, clipped.end.source_ref


def test_both_edges_clipped_cite_their_own_claims():
    iv = Interval(
        PreciseDate("2000-01-01", Precision.DAY, "claim_START"),
        PreciseDate("2010-12-31", Precision.DAY, "claim_END"),
    )
    c = iv.clip(not_before=date(2003, 4, 1), not_after=date(2005, 6, 30))
    assert "claim_START" in c.start.source_ref
    assert "claim_END" in c.end.source_ref
