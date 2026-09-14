"""Dates that carry their own precision, and intervals built from them.

WHY THIS EXISTS
---------------
Wikidata serves a year-precision date as the string "1984-01-01" with the
precision in a *separate* field (9 = year, 10 = month, 11 = day).  A parser
that reads the value and drops the precision manufactures a January 1st that
no source ever asserted.  Probed 2026-09-13: every P26/P451 statement returned
for the pilot subjects carried this shape.

So there is no constructor here for a date without a precision, and a
year-precision date is *stored* as "1984" rather than as a day that happens to
sit at the start of the year.  The January 1st cannot be written down, so it
cannot leak.

All exposure arithmetic returns fractions.Fraction, never float.  The two-year
worked example in the plan must come out as exactly 5120/731, and a float
would make that 7.004103967168262... with no way to prove it was right.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date
from enum import Enum
from fractions import Fraction

__all__ = [
    "Precision",
    "PreciseDate",
    "Interval",
    "Censoring",
    "WIKIDATA_PRECISION",
    "from_wikidata",
    "GAP_YEAR_DAYS",
]

# The declared gap-years convention.  Named, not inlined, because the plan
# publishes it and a test asserts the published number matches this constant.
GAP_YEAR_DAYS = Fraction(36525, 100)  # 365.25


class Precision(str, Enum):
    YEAR = "year"
    MONTH = "month"
    DAY = "day"


#: Wikidata timePrecision codes we accept.  Anything coarser than a year is
#: refused rather than silently widened: a decade-precision date is not a year.
WIKIDATA_PRECISION = {9: Precision.YEAR, 10: Precision.MONTH, 11: Precision.DAY}

_PATTERNS = {
    Precision.YEAR: re.compile(r"^-?\d{1,4}$"),
    Precision.MONTH: re.compile(r"^-?\d{1,4}-\d{2}$"),
    Precision.DAY: re.compile(r"^-?\d{1,4}-\d{2}-\d{2}$"),
}


class PrecisionError(ValueError):
    """Raised rather than guessing a precision or widening one."""


@dataclass(frozen=True, order=False)
class PreciseDate:
    """A date that knows how precisely it is known.

    ``value`` is stored truncated to its precision: "2016", "2016-05" or
    "2016-05-06".  ``source_ref`` is the id of the claim that supports it and
    is required, so an unsourced date cannot enter a record by accident.
    """

    value: str
    precision: Precision
    source_ref: str

    def __post_init__(self) -> None:
        if not isinstance(self.precision, Precision):
            raise PrecisionError(f"precision must be a Precision, got {self.precision!r}")
        if not _PATTERNS[self.precision].match(self.value):
            raise PrecisionError(
                f"value {self.value!r} is not in the shape required by precision "
                f"{self.precision.value!r}"
            )
        if not self.source_ref:
            raise PrecisionError("source_ref is required; an unsourced date is not a date")
        # Validate the calendar, which catches 2015-02-29 and month 13.
        self.earliest()
        self.latest()

    # -- bounds -----------------------------------------------------------
    def earliest(self) -> date:
        """The first day this date could denote."""
        p = self.value.split("-")
        if self.precision is Precision.YEAR:
            return date(int(p[0]), 1, 1)
        if self.precision is Precision.MONTH:
            return date(int(p[0]), int(p[1]), 1)
        return date(int(p[0]), int(p[1]), int(p[2]))

    def latest(self) -> date:
        """The last day this date could denote."""
        p = self.value.split("-")
        if self.precision is Precision.YEAR:
            return date(int(p[0]), 12, 31)
        if self.precision is Precision.MONTH:
            y, m = int(p[0]), int(p[1])
            return date(y, m, calendar.monthrange(y, m)[1])
        return date(int(p[0]), int(p[1]), int(p[2]))

    @property
    def year(self) -> int:
        return int(self.value.split("-")[0])

    def is_exact(self) -> bool:
        return self.precision is Precision.DAY

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.value} ({self.precision.value})"


def from_wikidata(value: str, time_precision: int, source_ref: str) -> PreciseDate:
    """Build a PreciseDate from a Wikidata time value plus its precision code.

    ``value`` arrives as "+1984-01-01T00:00:00Z" or "1984-01-01".  The day and
    month components are *discarded* when the precision says they are padding,
    which is the whole point of this function.
    """
    if time_precision not in WIKIDATA_PRECISION:
        raise PrecisionError(
            f"unsupported Wikidata timePrecision {time_precision}; "
            f"only {sorted(WIKIDATA_PRECISION)} (year/month/day) are accepted"
        )
    precision = WIKIDATA_PRECISION[time_precision]
    core = value.lstrip("+").split("T", 1)[0]
    parts = core.split("-")
    if len(parts) != 3:
        raise PrecisionError(f"unexpected Wikidata time value {value!r}")
    y, m, d = parts
    if precision is Precision.YEAR:
        return PreciseDate(str(int(y)), Precision.YEAR, source_ref)
    if precision is Precision.MONTH:
        return PreciseDate(f"{int(y):04d}-{m}", Precision.MONTH, source_ref)
    return PreciseDate(f"{int(y):04d}-{m}-{d}", Precision.DAY, source_ref)


class Censoring(str, Enum):
    CLOSED = "closed"      # a supported end date exists
    ONGOING = "ongoing"    # no supported end; ends at last_supported_active


@dataclass(frozen=True)
class Interval:
    """A half-open-in-spirit, closed-in-fact span of days.

    ``end`` is None only when ``censoring`` is ONGOING, and an ongoing interval
    is closed at ``last_supported_active`` -- NOT at the run date and NOT at the
    render date.  Those are three different timestamps and conflating them
    projects a relationship forward on no evidence.
    """

    start: PreciseDate
    end: PreciseDate | None
    censoring: Censoring = Censoring.CLOSED
    last_supported_active: PreciseDate | None = None

    def __post_init__(self) -> None:
        if self.censoring is Censoring.CLOSED and self.end is None:
            raise ValueError("a closed interval needs an end date")
        if self.censoring is Censoring.ONGOING:
            if self.end is not None:
                raise ValueError("an ongoing interval must not carry an end date")
            if self.last_supported_active is None:
                raise ValueError(
                    "an ongoing interval must carry last_supported_active; "
                    "it is what closes the interval, not the run date"
                )
        if self.first_day() > self.last_day():
            raise ValueError(
                f"interval ends ({self.last_day()}) before it starts ({self.first_day()})"
            )

    def first_day(self) -> date:
        return self.start.earliest()

    def last_day(self) -> date:
        if self.censoring is Censoring.ONGOING:
            assert self.last_supported_active is not None
            return self.last_supported_active.latest()
        assert self.end is not None
        return self.end.latest()

    def days(self) -> int:
        return (self.last_day() - self.first_day()).days + 1

    def clip(self, not_before: date | None = None, not_after: date | None = None) -> "Interval | None":
        """Return the part of this interval inside the bounds, or None.

        Used for the adult window.  The clipped interval keeps day precision on
        the clipped edge because the bound itself is exact, and keeps the
        original PreciseDate on any edge that was not moved.
        """
        lo, hi = self.first_day(), self.last_day()
        if not_before is not None and not_before > lo:
            lo = not_before
        if not_after is not None and not_after < hi:
            hi = not_after
        if lo > hi:
            return None
        start = (
            self.start
            if lo == self.first_day()
            else PreciseDate(lo.isoformat(), Precision.DAY, f"clip:{self.start.source_ref}")
        )
        if hi == self.last_day() and self.censoring is Censoring.CLOSED:
            return Interval(start, self.end, Censoring.CLOSED)
        if hi == self.last_day() and self.censoring is Censoring.ONGOING:
            return Interval(start, None, Censoring.ONGOING, self.last_supported_active)
        end = PreciseDate(hi.isoformat(), Precision.DAY, f"clip:{self.start.source_ref}")
        return Interval(start, end, Censoring.CLOSED)

    def year_shares(self) -> dict[int, Fraction]:
        """Exact share of this interval falling in each calendar year.

        Shares sum to exactly 1.  A two-calendar-year span across a leap year
        does NOT split 0.5/0.5: 2016-2017 is 366/731 and 365/731.
        """
        total = self.days()
        out: dict[int, Fraction] = {}
        lo, hi = self.first_day(), self.last_day()
        for y in range(lo.year, hi.year + 1):
            y_lo = max(lo, date(y, 1, 1))
            y_hi = min(hi, date(y, 12, 31))
            n = (y_hi - y_lo).days + 1
            if n > 0:
                out[y] = Fraction(n, total)
        return out

    def year_days(self) -> dict[int, int]:
        """Raw day counts per calendar year, for the gap-years convention."""
        out: dict[int, int] = {}
        lo, hi = self.first_day(), self.last_day()
        for y in range(lo.year, hi.year + 1):
            y_lo = max(lo, date(y, 1, 1))
            y_hi = min(hi, date(y, 12, 31))
            n = (y_hi - y_lo).days + 1
            if n > 0:
                out[y] = n
        return out
