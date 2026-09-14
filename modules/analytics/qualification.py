"""Who gets a rank, who appears unranked, and what the page must say either way.

The thresholds come from plan section 3.6. They are declared here as named
constants so a published number can never rest on a figure typed into prose.

THE SENTENCE THIS MODULE EXISTS TO FORCE
----------------------------------------
An incomplete signed total is NOT a conservative lower bound. The records that
are missing can be positive or negative, so a partially covered career total
can sit above or below the true one. Anything that reports a partial total
carries that sentence, and a test asserts it is present.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from modules.analytics.metrics import Pairing, covered_share, scored_weight

__all__ = [
    "MIN_FILMS", "MIN_EPISODES", "MIN_JOINT_COVERAGE", "MIN_FILMS_ABOVE_SINGLE_SOURCE",
    "MIN_SHARE_MONTH_PRECISION", "MAX_SHARE_NEARBY_REUSE",
    "PARTIAL_TOTAL_DISCLOSURE", "Qualification", "qualify",
]

MIN_FILMS = 3
MIN_EPISODES = 2
MIN_JOINT_COVERAGE = Fraction(3, 5)          # 0.60
MIN_FILMS_ABOVE_SINGLE_SOURCE = 2
MIN_SHARE_MONTH_PRECISION = Fraction(1, 2)   # 0.50
MAX_SHARE_NEARBY_REUSE = Fraction(2, 5)      # 0.40

PARTIAL_TOTAL_DISCLOSURE = (
    "Based on scored exposure only. An incomplete signed total is not a "
    "conservative lower bound: the missing records could be positive or "
    "negative, so the full-career total may be above or below this figure."
)


@dataclass(frozen=True)
class Qualification:
    person_id: str
    domain: str
    ranked: bool
    reasons: tuple[str, ...]
    distinct_pairings: int
    scored_pairings: int
    joint_coverage: Fraction
    share_month_precision: Fraction
    share_nearby_reuse: Fraction
    disclosure: str | None

    def as_dict(self) -> dict:
        return {
            "person_id": self.person_id, "domain": self.domain,
            "ranked": self.ranked, "reasons": list(self.reasons),
            "distinct_pairings": self.distinct_pairings,
            "scored_pairings": self.scored_pairings,
            "joint_coverage": float(self.joint_coverage),
            "share_month_precision": float(self.share_month_precision),
            "share_nearby_reuse": float(self.share_nearby_reuse),
            "disclosure": self.disclosure,
        }


def qualify(
    person_id: str,
    domain: str,
    pairings: list[Pairing],
    *,
    support_levels: dict[str, str] | None = None,
    period_precision: dict[str, str] | None = None,
    period_support: dict[str, str] | None = None,
) -> Qualification:
    """Decide whether a profile may carry a rank.

    Failing does NOT hide the profile. It appears unranked with its records
    visible, because an excluded name recorded is honest and an excluded name
    omitted looks like an oversight.
    """
    support_levels = support_levels or {}
    period_precision = period_precision or {}
    period_support = period_support or {}

    # An EMPTY period_support is a coherent statement: no nearby reuse
    # anywhere. A PARTIAL one is an oversight, and the two look identical to
    # `.get(eid)`, which returns None for both and counts the estimate as
    # contemporaneous. That UNDERSTATES share_nearby_reuse, and that share is
    # compared against a CAP -- so the understatement is in the direction that
    # lets a pairing qualify when it should not. Every other default in this
    # function errs the other way.
    if period_support:
        need = {eid for k in pairings for p in k.periods if p.both_scored
                for eid in (p.focal_estimate_id, p.partner_estimate_id) if eid}
        gaps = sorted(need - set(period_support))
        if gaps:
            raise ValueError(
                "period_support is populated but says nothing about "
                + ", ".join(gaps)
                + ". An absent estimate counts as contemporaneous, which lowers "
                "share_nearby_reuse toward the cap it is checked against. Pass "
                "'contemporaneous' explicitly, or pass an empty map to say "
                "there is no reuse anywhere."
            )

    scored = [k for k in pairings if covered_share(k) > 0]
    total_w = sum((scored_weight(k) for k in scored), Fraction(0))
    all_w = sum((k.w for k in pairings), Fraction(0))
    joint = total_w / all_w if all_w else Fraction(0)

    month_w = nearby_w = Fraction(0)
    for k in scored:
        for p in k.periods:
            if not p.both_scored:
                continue
            mass = k.w * p.q
            if period_precision.get(p.period, "year") in ("month", "day"):
                month_w += mass
            for eid in (p.focal_estimate_id, p.partner_estimate_id):
                if eid and period_support.get(eid) == "nearby_period":
                    nearby_w += mass
                    break
    share_month = month_w / total_w if total_w else Fraction(0)
    share_nearby = nearby_w / total_w if total_w else Fraction(0)

    minimum = MIN_FILMS if domain == "on_screen" else MIN_EPISODES
    reasons: list[str] = []
    if len(scored) < minimum:
        reasons.append(
            f"only {len(scored)} scored {'films' if domain == 'on_screen' else 'episodes'}, "
            f"needs {minimum}"
        )
    if joint < MIN_JOINT_COVERAGE:
        reasons.append(
            f"joint coverage {float(joint):.2f} below {float(MIN_JOINT_COVERAGE):.2f}"
        )
    if domain == "on_screen":
        above = sum(
            1 for k in scored
            if support_levels.get(k.pairing_id, "single_source") != "single_source"
        )
        if above < MIN_FILMS_ABOVE_SINGLE_SOURCE:
            reasons.append(
                f"only {above} scored films rest on more than a single source, "
                f"needs {MIN_FILMS_ABOVE_SINGLE_SOURCE}"
            )
    if share_month < MIN_SHARE_MONTH_PRECISION:
        reasons.append(
            f"only {float(share_month):.2f} of scored exposure is month-precision "
            f"or better; year-precision exposure requires the date sensitivity "
            f"shown on the row"
        )
    if share_nearby > MAX_SHARE_NEARBY_REUSE:
        reasons.append(
            f"{float(share_nearby):.2f} of scored exposure comes from nearby-period "
            f"reuse, above the {float(MAX_SHARE_NEARBY_REUSE):.2f} cap"
        )

    ranked = not reasons
    return Qualification(
        person_id=person_id, domain=domain, ranked=ranked,
        reasons=tuple(reasons), distinct_pairings=len(pairings),
        scored_pairings=len(scored), joint_coverage=joint,
        share_month_precision=share_month, share_nearby_reuse=share_nearby,
        disclosure=None if joint >= 1 else PARTIAL_TOTAL_DISCLOSURE,
    )
