"""The Partner_WAR baseline, frozen inside a metric release.

WHY IT IS FROZEN
----------------
    Partner_WAR_i = sum_k w(k) sum_t q(k,t) A(r,t)  -  B * scored_exposure_i

B multiplies exposure, so moving B changes existing totals at rates that differ
per person even when no fact about anybody changed. A two-pairing career and a
one-pairing career move by different amounts. That is not a relabelling, it is
a re-ranking, so B may only move with an explicit methodology version and a
disclosed recalculation.

The median partner estimate in the CURRENT cohort is kept as a descriptive
statistic printed beside the board. It is never the live baseline: recomputing
B from whichever rows happen to be scored this run would make every published
total depend on who else got scored.

THE COUNT-LIKE-BEHAVIOUR DIAGNOSTIC
-----------------------------------
If partner estimates barely vary, Partner_WAR becomes a disguised count of
recognized pairings.

R-squared of Partner_WAR on scored exposure is the WRONG test, and a failing
test caught it. Partner_WAR is a sum over exposure, so exposure dominates it by
construction: a deliberately varied fixture spanning partner estimates from 60
to 99 still produced R-squared 0.958. A diagnostic that fires on healthy data
is worse than none.

The right quantity is the spread of the PER-UNIT-EXPOSURE contribution,
Partner_WAR_i / scored_exposure_i. That equals the exposure-weighted mean of
(A_r - B), so it is exactly constant when every partner estimate is the same
and varies only when partner estimates genuinely differ. Its standard deviation
is in estimate points, which is a unit a reader can judge.

R-squared is still reported, as context. It does not decide anything.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from fractions import Fraction

from modules.analytics.metrics import (
    Pairing, partner_war, scored_exposure, scored_weight,
)

__all__ = [
    "MetricRelease", "CURRENT_RELEASE", "BaselineChangeError",
    "count_like_diagnostic", "CountLikeDiagnostic", "cohort_median_partner",
]


class BaselineChangeError(RuntimeError):
    pass


@dataclass(frozen=True)
class MetricRelease:
    """A named, frozen set of metric parameters."""

    version: str
    baseline: Fraction
    baseline_derivation: str
    #: Minimum spread, in estimate points, of the per-exposure contribution
    #: below which Partner_WAR is disclosed as count-like. None until set from
    #: real data.
    count_like_sd_threshold_points: float | None

    def with_baseline(self, new: Fraction, *, version: str, derivation: str
                      ) -> "MetricRelease":
        """Changing B is a new release, never an edit of this one."""
        if version == self.version:
            raise BaselineChangeError(
                f"changing the baseline from {self.baseline} to {new} requires a NEW "
                f"methodology version; {version!r} is the current one. Every "
                "published total must be recalculated and the change disclosed."
            )
        return MetricRelease(version, new, derivation,
                             self.count_like_sd_threshold_points)


#: Provisional. The baseline is NOT yet derived from real data: the M0 corpus
#: produced seven estimates spanning half a point, which cannot support a
#: meaningful replacement level. 85 is a placeholder that is declared as one.
CURRENT_RELEASE = MetricRelease(
    version="metric-release-0.1-provisional",
    baseline=Fraction(85),
    baseline_derivation=(
        "PLACEHOLDER, not derived from data. The pilot corpus spans half a point, "
        "which cannot support a replacement level. Must be re-derived, under a new "
        "version, before anything is published."
    ),
    count_like_sd_threshold_points=None,
)


def cohort_median_partner(pairings: list[Pairing]) -> float | None:
    """A DESCRIPTIVE statistic shown beside the board. Never the live baseline."""
    vals = [
        float(p.partner)
        for k in pairings for p in k.periods
        if p.both_scored
    ]
    return statistics.median(vals) if vals else None


@dataclass(frozen=True)
class CountLikeDiagnostic:
    contribution_sd: float | None    # the deciding quantity, in estimate points
    contribution_mean: float | None
    r_squared: float | None          # context only; never decides
    n: int
    threshold: float | None
    gates: bool
    disclosure_required: bool
    reading: str

    def as_dict(self) -> dict:
        return {
            "contribution_per_exposure_sd": self.contribution_sd,
            "contribution_per_exposure_mean": self.contribution_mean,
            "r_squared_context_only": self.r_squared,
            "n": self.n, "threshold_points": self.threshold,
            "gates": self.gates, "disclosure_required": self.disclosure_required,
            "reading": self.reading,
        }


def count_like_diagnostic(
    per_person: dict[str, list[Pairing]],
    release: MetricRelease = CURRENT_RELEASE,
) -> CountLikeDiagnostic:
    """Regress each person's Partner_WAR on their scored exposure, report R^2."""
    xs: list[float] = []
    ys: list[float] = []
    per_unit: list[float] = []
    for person, pairings in per_person.items():
        exposure = float(scored_exposure(pairings))
        if exposure == 0:
            continue
        war = float(partner_war(pairings, release.baseline))
        xs.append(exposure)
        ys.append(war)
        per_unit.append(war / exposure)

    n = len(xs)
    threshold = release.count_like_sd_threshold_points
    gates = threshold is not None
    if n < 3:
        return CountLikeDiagnostic(
            None, None, None, n, threshold, False, False,
            f"only {n} people with scored exposure; too few to judge",
        )

    sd = statistics.pstdev(per_unit)
    mean = statistics.mean(per_unit)

    # R^2 is context only. Partner_WAR is a sum over exposure, so exposure
    # dominates it and R^2 sits near 1 even on healthy data.
    mx, my = statistics.mean(xs), statistics.mean(ys)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    r2 = (sxy * sxy) / (sxx * syy) if sxx and syy else None

    required = bool(gates and sd <= threshold)
    if threshold is None:
        reading = (
            f"Per-exposure contribution {mean:.2f} +/- {sd:.2f} points. No "
            "threshold is set in this metric release, so this reports and does "
            "not gate."
        )
    elif required:
        reading = (
            f"Per-exposure contribution varies by only {sd:.2f} points, at or "
            f"below the declared {threshold:.2f}: Partner_WAR is behaving largely "
            "as a count of recognized pairings, and the page must say so."
        )
    else:
        reading = (
            f"Per-exposure contribution varies by {sd:.2f} points, above the "
            f"declared {threshold:.2f}."
        )
    return CountLikeDiagnostic(sd, mean, r2, n, threshold, gates, required, reading)
