"""The four leaderboards, from judged pairing gaps.

    PAW-WAR_i = C_i * (F_i - M_i)

read from the MAN's side: how much his partner outclassed him, which is what
"punching above his weight" means. The woman's side is the exact negation, so
boards 3 and 4 are not separate research -- they are the same numbers mirrored.

The judged `gap` is the source of truth, not the difference of the two absolute
scores. Both come from one call and the parser refuses a verdict where they
disagree, so they almost always match; where they do not, the gap is the number
the judge was actually asked for.

Exact arithmetic throughout. Gaps arrive as decimal strings like "0.4" and are
converted with ``Fraction(str(x))``, never ``Fraction(0.4)``, which would carry
the binary floating point error into every total.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction

__all__ = ["Contribution", "contributions_for", "paw_total", "paw_rate",
           "build_board", "exact"]


def exact(x: float | int | str) -> Fraction:
    """A decimal as an exact Fraction. ``Fraction(0.4)`` is not 2/5."""
    return Fraction(str(x))


@dataclass(frozen=True)
class Contribution:
    pairing_id: str
    domain: str
    period: str
    work: str | None
    other: str
    weight: Fraction        # centrality
    signed_gap: Fraction    # from THIS person's side: + means they punched up

    @property
    def paw(self) -> Fraction:
        return self.weight * self.signed_gap


def contributions_for(records: list[dict], qid: str) -> list[Contribution]:
    """Every scored pairing this person appears in, signed from their side.

    A man's signed gap is +gap (his partner scored above him). A woman's is
    -gap. That negation IS the mirroring, and it is exact rather than
    approximate: the same Fraction with its sign flipped.
    """
    out = []
    for r in records:
        if r.get("gap") is None:
            continue
        is_male = r.get("male_qid") == qid
        is_female = r.get("female_qid") == qid
        if not (is_male or is_female):
            continue
        # centrality None means the judge did not say; the pairing cannot be
        # weighted and is skipped rather than defaulted to 1.0. A default here
        # would silently promote an unclassified co-appearance to a full romance.
        c = r.get("centrality")
        if c is None:
            continue
        g = exact(r["gap"])
        out.append(Contribution(
            pairing_id=r["pairing_id"], domain=r["domain"], period=r["period"],
            work=r.get("work"),
            other=(r.get("female") if is_male else r.get("male")) or "?",
            weight=exact(c),
            signed_gap=g if is_male else -g,
        ))
    return out


def paw_total(cs: list[Contribution]) -> Fraction:
    return sum((c.paw for c in cs), Fraction(0))


def paw_rate(cs: list[Contribution]) -> Fraction | None:
    """Cumulative PAW per unit of scored exposure.

    Exposure is the summed centrality, so a person with many thin romances is
    not rewarded for volume the way the cumulative board rewards it. Returns
    None when the exposure is zero, never 0.0: no qualifying pairings is a
    different statement from an average of zero.
    """
    denom = sum((c.weight for c in cs), Fraction(0))
    if denom == 0:
        return None
    return paw_total(cs) / denom


def build_board(records: list[dict], *, gender: str, domain: str,
                names: dict[str, str], min_pairings: int = 1) -> list[dict]:
    """One leaderboard: one gender, one domain, sorted by cumulative PAW."""
    key = "male_qid" if gender == "male" else "female_qid"
    people = {r[key] for r in records if r.get(key)}
    rows = []
    for qid in people:
        cs = [c for c in contributions_for(records, qid) if c.domain == domain]
        # QUALIFYING pairings are those with non-zero weight. A person whose
        # only pairings are cast-list co-appearances has no romance to score,
        # and listing them at +0.00 reads as "measured, and came out even" --
        # the same confusion paw_rate returns None to avoid. Counting every
        # contribution here while excluding zero-weight ones there was
        # inconsistent: the board said nothing and zero were the same thing.
        scoring = [c for c in cs if c.weight != 0]
        if len(scoring) < min_pairings:
            continue
        cs = scoring
        rate = paw_rate(cs)
        rows.append({
            "qid": qid, "name": names.get(qid, qid),
            "pairings": len(cs),
            "exposure": float(sum((c.weight for c in cs), Fraction(0))),
            "paw_total": float(paw_total(cs)),
            "paw_rate": None if rate is None else float(rate),
            "contributions": [
                {"other": c.other, "work": c.work, "period": c.period,
                 "signed_gap": float(c.signed_gap), "weight": float(c.weight),
                 "paw": float(c.paw)}
                for c in sorted(cs, key=lambda c: -c.paw)
            ],
        })
    # -paw_total first, then the name: a stable tie-break that is not a judgement.
    rows.sort(key=lambda r: (-r["paw_total"], r["name"]))
    return rows
