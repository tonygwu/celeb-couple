"""Bounded nearby-period reuse.

An estimate may stand in for an adjacent period within a declared distance.
Two rules keep this from manufacturing precision.

ONE ESTIMATE, ONE IDENTITY. Reuse extends an existing estimate's ``periods``
list; it does not mint a second estimate. The sensitivity simulation draws each
estimate once, so a 2002 estimate reused for 2001 and 2003 moves as one thing
rather than as three independent values.

THE BOUND IS HARD. Beyond it the period is unscored with
``beyond_nearby_period_bound``, not scored from the nearest thing available.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["NEARBY_BOUND_YEARS", "resolve_period", "Resolution"]

#: Declared in the plan and asserted by a test. One year either side.
NEARBY_BOUND_YEARS = 1


@dataclass(frozen=True)
class Resolution:
    period: str
    source_period: str | None
    distance: int | None
    support: str            # "contemporaneous" | "nearby_period" | "unscored"
    reason: str | None = None

    @property
    def scored(self) -> bool:
        return self.source_period is not None


def resolve_period(
    wanted: str,
    available: dict[str, float | None],
    bound: int = NEARBY_BOUND_YEARS,
) -> Resolution:
    """Find an estimate for ``wanted``, allowing a bounded nearby year.

    ``available`` maps period -> estimate for ONE person. Exact match wins.
    Otherwise the closest year inside the bound wins, and ties break to the
    EARLIER year, deterministically, so a rerun cannot pick differently.
    """
    exact = available.get(wanted)
    if exact is not None:
        return Resolution(wanted, wanted, 0, "contemporaneous")

    try:
        target = int(wanted)
    except ValueError:
        return Resolution(wanted, None, None, "unscored", "period_not_a_year")

    candidates = []
    for period, value in available.items():
        if value is None:
            continue
        try:
            year = int(period)
        except ValueError:
            continue
        distance = abs(year - target)
        if distance <= bound:
            candidates.append((distance, year, period))
    if not candidates:
        return Resolution(wanted, None, None, "unscored", "beyond_nearby_period_bound")

    candidates.sort()               # nearest first, then earliest year
    distance, _, period = candidates[0]
    return Resolution(wanted, period, distance, "nearby_period")
