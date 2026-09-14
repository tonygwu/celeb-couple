"""Pairing metrics.  Pure functions: no network, no model call, no I/O.

Definitions, with A(p,t) the standing estimate for person p in period t,
k a qualifying film pairing or relationship episode, q(k,t) the temporal share
within k, and w(k) its exposure weight:

    S(k)             = periods where BOTH people have eligible estimates
    covered_share(k) = sum over S(k) of q(k,t)
    gap(p,k)         = sum over S(k) of q(k,t)*[A(r,t) - A(p,t)] / covered_share(k)
    scored_weight(k) = w(k) * covered_share(k)
    PAW_total(p)     = sum over k of scored_weight(k) * gap(p,k)
    PAW_rate(p)      = PAW_total(p) / sum over k of scored_weight(k)
    Partner_WAR(p)   = sum over k of w(k) * sum over S(k) of q(k,t)*[A(r,t) - B]

Everything is exact.  Estimates enter through ``as_estimate`` which converts
via the decimal string, so 78.3 becomes Fraction(783, 10) and not the nearest
binary double.  Rounding happens at display and nowhere else.

Zero coverage produces an UNSCORED pairing, never a zero and never a division.
A pairing with one side unscored is removed from BOTH mirrored gender views,
because a gap needs two estimates.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Mapping

__all__ = [
    "as_estimate",
    "PeriodExposure",
    "Pairing",
    "covered_share",
    "gap",
    "scored_weight",
    "scored_exposure",
    "paw_total",
    "paw_rate",
    "partner_war",
    "gap_years",
    "GAP_YEAR_DAYS",
]

from packages.temporal.dates import GAP_YEAR_DAYS


def as_estimate(x: float | int | Fraction | None) -> Fraction | None:
    """Convert a displayed estimate to an exact Fraction, or pass through None."""
    if x is None:
        return None
    if isinstance(x, Fraction):
        return x
    return Fraction(str(x))


@dataclass(frozen=True)
class PeriodExposure:
    """One period inside one pairing, with both sides' estimates.

    ``focal_estimate_id`` and ``partner_estimate_id`` identify WHICH estimate
    supplied the value.  The sensitivity simulation keys its draws on those ids,
    so one estimate reused across three periods moves as one thing.
    """

    period: str
    q: Fraction
    focal: Fraction | None
    partner: Fraction | None
    focal_estimate_id: str | None = None
    partner_estimate_id: str | None = None
    days: int | None = None

    @property
    def both_scored(self) -> bool:
        return self.focal is not None and self.partner is not None


@dataclass(frozen=True)
class Pairing:
    """A film pairing or a relationship episode, from one person's side."""

    pairing_id: str
    focal_id: str
    partner_id: str
    domain: str                       # "on_screen" | "real_life"
    periods: tuple[PeriodExposure, ...]
    w: Fraction = Fraction(1)

    def __post_init__(self) -> None:
        """The temporal shares must partition the pairing exactly.

        `q` is a SHARE of the pairing's exposure, so the shares across all its
        periods sum to 1 by definition. Nothing checked it. A pairing whose
        shares summed to 1.5 would give `covered_share` 1.5 and
        `scored_weight` w*1.5, silently overweighting it in every total -- and
        `covered_share` is what the qualification threshold compares against,
        so an unqualified pairing could pass on arithmetic that cannot be right.

        Empty is allowed: a pairing with no eligible periods is a real state
        and is reported as unscored.
        """
        if not self.periods:
            return
        total = sum((p.q for p in self.periods), Fraction(0))
        if total != 1:
            raise ValueError(
                f"pairing {self.pairing_id!r}: temporal shares sum to {total}, "
                f"not 1. q is a share of this pairing's exposure, so the "
                f"periods must partition it exactly. Periods: "
                + ", ".join(f"{p.period}={p.q}" for p in self.periods)
            )

    def scored_periods(self) -> tuple[PeriodExposure, ...]:
        return tuple(p for p in self.periods if p.both_scored)

    def mirror(self) -> "Pairing":
        """The same pairing seen from the partner's side."""
        return Pairing(
            pairing_id=self.pairing_id,
            focal_id=self.partner_id,
            partner_id=self.focal_id,
            domain=self.domain,
            w=self.w,
            periods=tuple(
                PeriodExposure(
                    period=p.period, q=p.q,
                    focal=p.partner, partner=p.focal,
                    focal_estimate_id=p.partner_estimate_id,
                    partner_estimate_id=p.focal_estimate_id,
                    days=p.days,
                )
                for p in self.periods
            ),
        )


def covered_share(k: Pairing) -> Fraction:
    return sum((p.q for p in k.scored_periods()), Fraction(0))


def gap(k: Pairing) -> Fraction | None:
    """Exposure-weighted signed gap, or None when the pairing is unscored."""
    cs = covered_share(k)
    if cs == 0:
        return None
    total = sum(
        (p.q * (p.partner - p.focal) for p in k.scored_periods()), Fraction(0)
    )
    return total / cs


def scored_weight(k: Pairing) -> Fraction:
    return k.w * covered_share(k)


def scored_exposure(pairings: Iterable[Pairing]) -> Fraction:
    return sum((scored_weight(k) for k in pairings), Fraction(0))


def paw_total(pairings: Iterable[Pairing]) -> Fraction:
    total = Fraction(0)
    for k in pairings:
        g = gap(k)
        if g is not None:
            total += scored_weight(k) * g
    return total


def paw_rate(pairings: Iterable[Pairing]) -> Fraction | None:
    ps = list(pairings)
    denom = scored_exposure(ps)
    if denom == 0:
        return None
    return paw_total(ps) / denom


def partner_war(pairings: Iterable[Pairing], baseline: Fraction) -> Fraction:
    """Partner mass above a FROZEN baseline.

    B is frozen inside the metric release.  Because B multiplies exposure,
    changing it moves existing totals at rates that differ per person even when
    no fact about them changed, so it may only move with a methodology version.
    """
    total = Fraction(0)
    for k in pairings:
        total += k.w * sum(
            (p.q * (p.partner - baseline) for p in k.scored_periods()), Fraction(0)
        )
    return total


def gap_years(k: Pairing) -> Fraction | None:
    """Accumulated gap weighted by eligible days, in years of days/365.25.

    A separate unit from the episode-weighted gap.  The two are never added
    together, and neither is ever added to film-pair units.
    """
    scored = k.scored_periods()
    if not scored:
        return None
    if any(p.days is None for p in scored):
        raise ValueError(
            f"{k.pairing_id}: gap-years needs day counts on every scored period"
        )
    return sum(
        ((p.partner - p.focal) * Fraction(p.days) / GAP_YEAR_DAYS for p in scored),
        Fraction(0),
    )


def apply_cross_gender_offset(k: Pairing, delta: Fraction) -> Pairing:
    """Add delta to the PARTNER side only, for the offset sensitivity diagnostic.

    Adding a constant delta to every opposite-gender estimate raises every gap
    by delta, so PAW_total moves by delta * scored_exposure and PAW_rate moves
    by exactly delta.  PAW-rate RANKS within a view therefore cannot move.
    """
    return Pairing(
        pairing_id=k.pairing_id, focal_id=k.focal_id, partner_id=k.partner_id,
        domain=k.domain, w=k.w,
        periods=tuple(
            PeriodExposure(
                period=p.period, q=p.q, focal=p.focal,
                partner=None if p.partner is None else p.partner + delta,
                focal_estimate_id=p.focal_estimate_id,
                partner_estimate_id=p.partner_estimate_id,
                days=p.days,
            )
            for p in k.periods
        ),
    )
