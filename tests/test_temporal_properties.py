"""Property-based tests for date precision and exposure arithmetic."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from fractions import Fraction as F

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from packages.temporal.dates import (
    Censoring, Interval, Precision, PreciseDate, from_wikidata,
)

years = st.integers(min_value=1900, max_value=2099)
months = st.integers(min_value=1, max_value=12)


@st.composite
def precise_date(draw, precision=None):
    p = precision or draw(st.sampled_from(list(Precision)))
    y = draw(years)
    if p is Precision.YEAR:
        return PreciseDate(f"{y}", p, "c")
    m = draw(months)
    if p is Precision.MONTH:
        return PreciseDate(f"{y}-{m:02d}", p, "c")
    d = draw(st.integers(1, calendar.monthrange(y, m)[1]))
    return PreciseDate(f"{y}-{m:02d}-{d:02d}", p, "c")


@st.composite
def interval(draw):
    a = draw(precise_date())
    span = draw(st.integers(min_value=0, max_value=4000))
    lo = a.earliest()
    hi = lo + timedelta(days=span)
    return Interval(PreciseDate(lo.isoformat(), Precision.DAY, "c"),
                    PreciseDate(hi.isoformat(), Precision.DAY, "c"))


@given(precise_date())
@settings(max_examples=400, deadline=None)
def test_earliest_never_exceeds_latest(d):
    assert d.earliest() <= d.latest()


@given(precise_date(precision=Precision.YEAR))
@settings(max_examples=300, deadline=None)
def test_a_year_precision_date_spans_its_whole_year(d):
    assert d.earliest() == date(d.year, 1, 1)
    assert d.latest() == date(d.year, 12, 31)
    assert "-" not in d.value, "a year must not be stored as a padded day"


@given(years, months, st.integers(1, 28))
@settings(max_examples=300, deadline=None)
def test_wikidata_precision_always_truncates_to_what_it_claims(y, m, d):
    padded = f"+{y:04d}-{m:02d}-{d:02d}T00:00:00Z"
    assert from_wikidata(padded, 9, "c").value == str(y)
    assert from_wikidata(padded, 10, "c").value == f"{y:04d}-{m:02d}"
    assert from_wikidata(padded, 11, "c").value == f"{y:04d}-{m:02d}-{d:02d}"


@given(interval())
@settings(max_examples=300, deadline=None)
def test_year_shares_always_sum_to_exactly_one(iv):
    shares = iv.year_shares()
    assert sum(shares.values()) == 1
    assert all(s > 0 for s in shares.values())


@given(interval())
@settings(max_examples=300, deadline=None)
def test_year_days_sum_to_the_interval_length(iv):
    assert sum(iv.year_days().values()) == iv.days()


@given(interval())
@settings(max_examples=300, deadline=None)
def test_shares_are_exactly_days_over_total(iv):
    total = iv.days()
    for y, share in iv.year_shares().items():
        assert share == F(iv.year_days()[y], total)


@given(interval(), st.integers(min_value=0, max_value=3000))
@settings(max_examples=300, deadline=None)
def test_clipping_never_lengthens_an_interval(iv, offset):
    bound = iv.first_day() + timedelta(days=offset)
    clipped = iv.clip(not_before=bound)
    if clipped is not None:
        assert clipped.days() <= iv.days()
        assert clipped.first_day() >= iv.first_day()
        assert clipped.last_day() <= iv.last_day()


@given(interval())
@settings(max_examples=200, deadline=None)
def test_clipping_to_the_interval_itself_is_a_no_op(iv):
    same = iv.clip(not_before=iv.first_day(), not_after=iv.last_day())
    assert same is not None
    assert same.days() == iv.days()
    assert same.year_shares() == iv.year_shares()


@given(precise_date(precision=Precision.DAY), st.integers(1, 3000))
@settings(max_examples=200, deadline=None)
def test_an_ongoing_interval_never_runs_past_its_last_supported_activity(start, span):
    last = start.earliest() + timedelta(days=span)
    iv = Interval(start, None, Censoring.ONGOING,
                  PreciseDate(last.isoformat(), Precision.DAY, "c"))
    assert iv.last_day() == last
    assert max(iv.year_shares()) == last.year
