"""Is a pairing's gap comparing two people, or two publication formats?

Evidence type alone explains a large share of the variance in the standing
estimates -- the current figure is in `data/pilot/run/shape_confound.json` and
is deliberately not written down here, because a hand-typed measurement goes
stale and then lies. An editorial award is superlative by construction and
concentrates near the top of the scale; ranked placements spread lower. So when one side of a pairing is
judged by an award and the other by a list placement, a large part of the
signed gap is a statement about which magazine covered whom in what format.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not correct for the confound. Normalising within shape would silently
change what the number means, and the plan forbids exactly that kind of quiet
recentring. Instead it LABELS each pairing, so a comparable gap and a
manufactured one can never be read as the same thing, and so a same-shape view
can be computed as a declared sensitivity scenario beside the main board.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from modules.analytics.metrics import Pairing, covered_share, paw_total

__all__ = ["Comparability", "classify_pairing", "COMPARABLE", "MISMATCHED",
           "UNKNOWN_SHAPE", "MISMATCH_CAVEAT", "same_shape_view"]

COMPARABLE = "comparable"
MISMATCHED = "shape_mismatched"
UNKNOWN_SHAPE = "shape_unknown"

MISMATCH_CAVEAT = (
    "The two sides of this pairing are judged by different kinds of evidence. "
    "An award is superlative by construction and scores near the top of the "
    "scale; a list placement spreads lower. A large part of this gap reflects "
    "which publication covered whom in what format, not the two people."
)


@dataclass(frozen=True)
class Comparability:
    pairing_id: str
    status: str
    a_shape: str
    b_shape: str
    caveat: str | None

    @property
    def comparable(self) -> bool:
        return self.status == COMPARABLE

    def as_dict(self) -> dict:
        return {"pairing_id": self.pairing_id, "status": self.status,
                "a_shape": self.a_shape, "b_shape": self.b_shape,
                "caveat": self.caveat}


def classify_pairing(pairing_id: str, a_shape: str | None, b_shape: str | None
                     ) -> Comparability:
    if not a_shape or not b_shape:
        return Comparability(pairing_id, UNKNOWN_SHAPE, a_shape or "", b_shape or "",
                             "The evidence shape on at least one side is unknown.")
    if a_shape == b_shape:
        return Comparability(pairing_id, COMPARABLE, a_shape, b_shape, None)
    return Comparability(pairing_id, MISMATCHED, a_shape, b_shape, MISMATCH_CAVEAT)


def same_shape_view(
    pairings: list[Pairing], shapes: dict[str, tuple[str | None, str | None]]
) -> dict:
    """Recompute the board over comparable pairings only, as a labelled scenario.

    Returns both totals so the difference is inspectable. This is a SENSITIVITY
    VIEW, not a correction: the main board still shows every scored pairing, and
    dropping the mismatched ones answers a different question.
    """
    classified = [
        classify_pairing(k.pairing_id, *shapes.get(k.pairing_id, (None, None)))
        for k in pairings
    ]
    by_id = {c.pairing_id: c for c in classified}
    comparable = [k for k in pairings if by_id[k.pairing_id].comparable]
    scored = [k for k in pairings if covered_share(k) > 0]

    return {
        "view": "same-shape sensitivity",
        "is_a_correction": False,
        "explanation": (
            "The main board keeps every scored pairing. This scenario keeps only "
            "pairings whose two sides carry the same kind of evidence, which "
            "answers a different and narrower question: what the gaps look like "
            "when format cannot be the explanation."
        ),
        "scored_pairings": len(scored),
        "comparable_pairings": len(comparable),
        "mismatched_pairings": sum(1 for c in classified if c.status == MISMATCHED),
        "unknown_shape_pairings": sum(1 for c in classified if c.status == UNKNOWN_SHAPE),
        "paw_total_all_scored": float(paw_total(scored)),
        "paw_total_comparable_only": float(paw_total(comparable)),
        "classifications": [c.as_dict() for c in classified],
    }
