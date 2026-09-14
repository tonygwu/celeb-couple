"""Sensitivity intervals for the pairing metrics.

WHAT THIS IS, AND WHAT IT IS NOT
--------------------------------
This is a SENSITIVITY interval: it says how much a published total moves when
the standing estimates are perturbed by a declared amount. It is NOT a
calibrated confidence interval, nothing here calls it one, and the assumption
set travels with every result so a reader can see what was assumed.

Three things it deliberately does not try to quantify: missing relationships,
missing list editions, and publisher selection bias. Those are coverage
denominators on the page, not an interval, because widening a bar does not
represent a record nobody has.

WHY DRAWS ARE SHARED
--------------------
Each STANDING ESTIMATE is drawn once per simulation and that single draw is
used everywhere the estimate appears. Two consequences, and both are invariants
rather than niceties:

  1. A mirrored gap stays an exact negative in every single draw, because both
     views read the same two numbers.
  2. An estimate reused across adjacent periods under the nearby-period bound
     moves as ONE thing. Drawing it separately per period key would invent
     precision that the single underlying observation cannot support.

An optional publisher effect is drawn once per publisher per simulation, for
the same reason: two estimates resting on the same magazine do not have
independent errors.
"""

from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field
from fractions import Fraction

from modules.analytics.metrics import (
    Pairing, PeriodExposure, paw_rate, paw_total,
)

__all__ = ["EstimateSpec", "SensitivityResult", "simulate", "DEFAULT_DRAWS", "DEFAULT_SEED"]

#: Enough that the Monte Carlo error on a percentile endpoint is well under a
#: tenth of a point, and cheap because nothing here calls a model.
DEFAULT_DRAWS = 20000
#: Seeded, so published endpoints do not drift between runs of the same inputs.
DEFAULT_SEED = 20260914


@dataclass(frozen=True)
class EstimateSpec:
    """One standing estimate and how far it is allowed to move.

    ``sd`` combines the two quantified components from the plan: measured rater
    spread, and the rubric-declared support band. Both are widths in estimate
    points.
    """

    estimate_id: str
    value: float
    sd: float
    publisher: str | None = None


@dataclass(frozen=True)
class SensitivityResult:
    point_total: float
    point_rate: float | None
    total_low: float
    total_high: float
    rate_low: float | None
    rate_high: float | None
    draws: int
    seed: int
    interval: str
    assumptions: dict
    mirror_checked: bool = False

    def as_dict(self) -> dict:
        return {
            "type": "sensitivity",
            "not_a_confidence_interval": (
                "This is a sensitivity interval over declared perturbations of the "
                "standing estimates. It is not a calibrated confidence interval."
            ),
            "point_total": self.point_total, "point_rate": self.point_rate,
            "total_interval": [self.total_low, self.total_high],
            "rate_interval": [self.rate_low, self.rate_high],
            "draws": self.draws, "seed": self.seed, "interval": self.interval,
            "assumptions": self.assumptions,
            "mirror_invariant_checked": self.mirror_checked,
        }


def _required_estimate_ids(pairings: list[Pairing]) -> set[str]:
    """Every estimate id the pairings actually read a value through."""
    need: set[str] = set()
    for k in pairings:
        for p in k.periods:
            if p.focal is not None and p.focal_estimate_id:
                need.add(p.focal_estimate_id)
            if p.partner is not None and p.partner_estimate_id:
                need.add(p.partner_estimate_id)
    return need


def _redraw(pairings: list[Pairing], drawn: dict[str, float]) -> list[Pairing]:
    """Rebuild pairings substituting drawn values BY ESTIMATE ID.

    This is why PeriodExposure carries focal_estimate_id and
    partner_estimate_id: substitution keyed on the id is what makes one
    estimate move as one thing wherever it appears.
    """
    out = []
    for k in pairings:
        periods = []
        for p in k.periods:
            f = drawn.get(p.focal_estimate_id) if p.focal_estimate_id else None
            g = drawn.get(p.partner_estimate_id) if p.partner_estimate_id else None
            periods.append(PeriodExposure(
                period=p.period, q=p.q,
                focal=None if p.focal is None else (
                    Fraction(str(round(f, 6))) if f is not None else p.focal),
                partner=None if p.partner is None else (
                    Fraction(str(round(g, 6))) if g is not None else p.partner),
                focal_estimate_id=p.focal_estimate_id,
                partner_estimate_id=p.partner_estimate_id,
                days=p.days,
            ))
        out.append(Pairing(k.pairing_id, k.focal_id, k.partner_id, k.domain,
                           tuple(periods), k.w))
    return out


def simulate(
    pairings: list[Pairing],
    specs: dict[str, EstimateSpec],
    *,
    draws: int = DEFAULT_DRAWS,
    seed: int = DEFAULT_SEED,
    publisher_sd: float = 0.0,
    alpha: float = 0.05,
    check_mirror: bool = True,
) -> SensitivityResult:
    """Perturb the estimates and report where the total lands.

    ``check_mirror`` verifies on the first draw that every pairing's mirrored
    gap is the exact negative of its own. It is on by default because a shared
    draw that silently stopped being shared would break that identity, and a
    broken identity is the failure this whole design exists to prevent.
    """
    missing = sorted(_required_estimate_ids(pairings) - set(specs))
    if missing:
        raise ValueError(
            "no EstimateSpec for "
            + ", ".join(missing)
            + ". Every estimate a pairing reads must declare how far it may "
            "move. Without a spec the draw falls back to the unperturbed "
            "value, which silently NARROWS the interval -- an empty spec map "
            "produced a zero-width one, and a zero-width sensitivity interval "
            "reads as certainty. An estimate that genuinely should not move "
            "takes a spec with sd=0.0, so the choice is visible here rather "
            "than implied by an omission."
        )

    rng = random.Random(seed)
    point_total = float(paw_total(pairings))
    pr = paw_rate(pairings)
    point_rate = None if pr is None else float(pr)

    totals: list[float] = []
    rates: list[float] = []
    mirror_ok = False

    for i in range(draws):
        pub_effect: dict[str, float] = {}
        drawn: dict[str, float] = {}
        for eid, spec in specs.items():
            if publisher_sd and spec.publisher is not None:
                if spec.publisher not in pub_effect:
                    pub_effect[spec.publisher] = rng.gauss(0.0, publisher_sd)
                shift = pub_effect[spec.publisher]
            else:
                shift = 0.0
            # ONE draw per estimate, reused everywhere that estimate appears
            drawn[eid] = min(100.0, max(0.0, rng.gauss(spec.value, spec.sd) + shift))

        perturbed = _redraw(pairings, drawn)
        if i == 0 and check_mirror:
            from modules.analytics.metrics import gap
            mirror_ok = all(
                (gap(k) is None and gap(k.mirror()) is None)
                or gap(k) == -gap(k.mirror())
                for k in perturbed
            )
        totals.append(float(paw_total(perturbed)))
        r = paw_rate(perturbed)
        if r is not None:
            rates.append(float(r))

    def band(xs: list[float]) -> tuple[float | None, float | None]:
        if not xs:
            return None, None
        xs = sorted(xs)
        lo = xs[int((alpha / 2) * len(xs))]
        hi = xs[min(int((1 - alpha / 2) * len(xs)), len(xs) - 1)]
        return lo, hi

    tl, th = band(totals)
    rl, rh = band(rates)
    return SensitivityResult(
        point_total=point_total, point_rate=point_rate,
        total_low=tl, total_high=th, rate_low=rl, rate_high=rh,
        draws=draws, seed=seed, interval=f"{int((1 - alpha) * 100)}%",
        assumptions={
            "per_estimate_sd": {k: v.sd for k, v in specs.items()},
            "publisher_sd": publisher_sd,
            "draw_sharing": (
                "one draw per standing estimate, reused across every period and "
                "every pairing that estimate serves"
            ),
            "not_quantified": [
                "missing relationships", "missing list editions",
                "publisher selection bias",
            ],
        },
        mirror_checked=mirror_ok,
    )
