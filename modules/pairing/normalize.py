"""Within-sex normalization of the absolute scores, as a SECOND board view.

This never replaces the raw board. Plan v3 put `same_shape_view` beside the
main board rather than over it, for the reason
`modules/analytics/comparability.py` states in its own header: normalising
inside a group silently changes what the number means, so the corrected view
has to be labelled and shown next to the uncorrected one. The same rule holds
here. `scripts/build_boards.py` renders the raw board first and this one after
it, under its own heading.

WHAT THE POPULATION IS
----------------------
The operator's specification, which is load-bearing:

    "the normalization should be among all (Male x Time-Slice) tuples"

A person is judged at the time of each pairing, so Adam Sandler in 2011 is a
different observation from Adam Sandler in 2004. The population is therefore
(sex, person, period) TUPLES within one sex, not one score per person. A person
judged in three periods contributes three observations. A person judged in five
pairings inside ONE period contributes one, whose score is the mean of the five.

Three further choices, made here rather than left implicit:

- **The two judge families are separate populations.** An absolute score only
  means anything on the scale of the judge that produced it, and the two
  families do not share one: measured on the stored verdicts, astra scores the
  women 0.354 above the men with an sd ratio of 0.78, fable 0.476 with a ratio
  of 0.96. Pooling them would normalize away part of the family difference and
  call it a sex difference. Each family is normalized on its own, and the
  per-pairing results are then averaged across families exactly as
  `merge_families` already averages raw gaps.
- **The two domains are pooled.** On-screen and real-life pairings both carry a
  year, and a (person, year) tuple is one observation whichever produced it.
  Only 9 of 215 person-period tuples are reached by both domains, so this is a
  small choice, but it is a choice.
- **The sd is the SAMPLE sd** (n-1 denominator), matching `statistics.stdev`,
  which the rest of this repository uses. At n around 90 that is 0.6% larger
  than the population sd. Because the two sexes have different n, the choice is
  not quite a common rescale, but the difference between the two cells is under
  0.1% and cannot move a rank.

WHY Z-SCORE, AND NOT MIN-MAX OR PERCENTILE
------------------------------------------
n is about 77 to 107 observations per (family, sex) cell. All three candidates
were considered against that n and against the measured shape of the scores.

**Min-max: rejected.** Its two parameters are two single observations, so the
scale for all 90 astra men is set by the one verdict at 6.5 and the one at 9.7.
One re-judged pairing rewrites every normalized score in the cell. At this n
that is not a robustness quibble, it is the likeliest failure.

**Percentile / rank: rejected, on a measured property of this corpus.** The
judges answer to one decimal inside a narrow band, so astra's 100 female
verdicts take only 14 distinct values. Ranking a population that is mostly ties
hands the tie-breaking rule more influence over the ordering than the judgments
have. Rank normalization also discards magnitude: it would make the step from
9.6 to 9.7 the same size as the step from 7.0 to 8.2 whenever the counts match.
The board's quantity is a magnitude in rubric points and its error bar (the
cross-family floor, about 0.28 points) is in the same units, so a unitless
percentile board could not be checked against it at all.

**Z-score: chosen.** Both parameters use the whole sample, so no single verdict
controls the scale; it is an affine map, which is what the board's additive
arithmetic wants; and it rescales as well as shifts, which is the part that a
constant offset cannot do.

The z-scores are then mapped back onto the family's own scale:

    normalized(x) = mu_family + sd_family * (x - mu_sex) / sd_sex

The map is affine and identical within a sex, so it changes no ordering. What
it buys is that the output stays in rubric points, so the 0.28-point
cross-family floor still applies to the normalized board.

WHAT IT COSTS, PLAINLY
----------------------
1. **The mean normalized gap is zero by construction.** That is the point and
   the cost together. The normalized view can never answer "do the judges score
   women higher than men"; it has assumed the answer is no. The raw board is
   the one that carries that measured +0.43, and it stays the default.
2. **Z-score assumes rough symmetry and is not robust to outliers.** A
   median/IQR version would be, at the price of using two order statistics from
   a heavily tied sample -- the same defect that ruled out percentile.
3. **It equalizes the two sexes' spreads, which may not be an artifact.** If
   the women's narrower sd is a real fact about who gets cast, normalization
   deletes a finding. Nothing in these data decides which it is.
4. **It is computed from the two ABSOLUTE scores, not from the judged gap**,
   which plan v4 section 4 demotes deliberately. On this corpus that costs
   nothing measurable: over all 219 judged verdicts the largest value of
   |(f_absolute - m_absolute) - gap| is 0.0000. The parser refuses a verdict
   whose absolutes contradict its gap, so the two can never diverge far, but
   this view depends on absolutes in a way the raw board does not.

EXACT ARITHMETIC
----------------
Means and variances are exact `Fraction`s, built with `Fraction(str(x))` and
never `Fraction(0.4)`, for the reason `modules/pairing/boards.py` gives. The
one place exactness cannot hold is the square root in the sd. It is taken in
`Decimal` at 50 significant digits, which is correctly rounded and
deterministic on every platform, and converted back to an exact Fraction. Every
later step is exact over that rational.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

from modules.pairing.boards import exact
from modules.pairing.judge import ParseError, parse_pairing_verdict

__all__ = ["NotNormalizable", "Observation", "Scale", "SQRT_DIGITS",
           "observations", "population", "scales", "normalize_population",
           "normalized_gaps", "normalized_records", "load_raw_verdicts",
           "rank_changes"]

#: Significant digits used for the one square root in the whole module.
SQRT_DIGITS = 50

#: `<pairing_id>__<family>.txt` is how score_pairings.py names a raw verdict.
_RAW_NAME = re.compile(r"^(?P<pid>.+)__(?P<family>[a-z0-9]+)$")


class NotNormalizable(ValueError):
    """Refuses rather than guessing. A cell with no spread, a verdict that
    matches no pairing record, or a population too small to have a sample sd
    are all cases where a default would be a silent wrong answer."""


@dataclass(frozen=True)
class Observation:
    """One judged appearance of one person at one time slice."""
    family: str
    sex: str
    qid: str
    period: str
    score: Fraction

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.family, self.sex, self.qid, self.period)


@dataclass(frozen=True)
class Scale:
    """The two parameters of one normalization cell, and the n behind them."""
    family: str
    sex: str
    n: int
    mean: Fraction
    sd: Fraction

    def as_dict(self) -> dict:
        return {"family": self.family, "sex": self.sex, "n": self.n,
                "mean": float(self.mean), "sd": float(self.sd)}


def _sqrt(x: Fraction) -> Fraction:
    """The only inexact step. Correctly rounded at SQRT_DIGITS, then exact."""
    if x < 0:
        raise NotNormalizable(f"negative variance {x}")
    if x == 0:
        return Fraction(0)
    with localcontext() as ctx:
        ctx.prec = SQRT_DIGITS
        root = (Decimal(x.numerator) / Decimal(x.denominator)).sqrt()
    return Fraction(root)


def _mean(xs: list[Fraction]) -> Fraction:
    return sum(xs, Fraction(0)) / len(xs)


def _sample_sd(xs: list[Fraction]) -> Fraction:
    if len(xs) < 2:
        raise NotNormalizable(
            f"a sample sd needs at least 2 observations, got {len(xs)}")
    mu = _mean(xs)
    var = sum(((x - mu) ** 2 for x in xs), Fraction(0)) / (len(xs) - 1)
    return _sqrt(var)


def observations(verdicts: list[dict]) -> list[Observation]:
    """Two observations per verdict: the woman's and the man's.

    A verdict is a dict with `family`, `pairing_id`, `male_qid`, `female_qid`,
    `period`, `f_absolute` and `m_absolute`. `load_raw_verdicts` builds them
    from the stored raw files; the tests build them by hand.
    """
    out: list[Observation] = []
    for v in verdicts:
        if v.get("f_absolute") is None or v.get("m_absolute") is None:
            continue
        out.append(Observation(v["family"], "female", v["female_qid"],
                               str(v["period"]), exact(v["f_absolute"])))
        out.append(Observation(v["family"], "male", v["male_qid"],
                               str(v["period"]), exact(v["m_absolute"])))
    return out


def population(obs: list[Observation]) -> dict[tuple[str, str, str, str], Fraction]:
    """Collapse to one score per (family, sex, person, period) TUPLE.

    This is the operator's rule applied literally: the population is the set of
    tuples, so five judgments of one person-period are one observation carrying
    their exact mean, while three periods of the same person are three.
    """
    buckets: dict[tuple[str, str, str, str], list[Fraction]] = {}
    for o in obs:
        buckets.setdefault(o.key, []).append(o.score)
    return {k: _mean(v) for k, v in buckets.items()}


def scales(pop: dict[tuple[str, str, str, str], Fraction]
           ) -> dict[tuple[str, str], Scale]:
    """One Scale per (family, sex) cell, plus a (family, "*") grand cell.

    The grand cell is the target scale: normalized scores are mapped onto the
    family's own mean and sd so they stay in rubric points.
    """
    cells: dict[tuple[str, str], list[Fraction]] = {}
    for (family, sex, _qid, _period), score in pop.items():
        cells.setdefault((family, sex), []).append(score)
        cells.setdefault((family, "*"), []).append(score)
    out: dict[tuple[str, str], Scale] = {}
    for (family, sex), xs in cells.items():
        try:
            sd = _sample_sd(xs)
        except NotNormalizable as exc:
            raise NotNormalizable(
                f"cell ({family}, {sex}) has {len(xs)} observations: {exc}"
            ) from exc
        if sd == 0:
            raise NotNormalizable(
                f"cell ({family}, {sex}) has zero spread over {len(xs)} "
                f"observations, so there is nothing to divide by. Returning "
                f"the raw score, or zero, would be a silent wrong answer.")
        out[(family, sex)] = Scale(family, sex, len(xs), _mean(xs), sd)
    return out


def normalize_population(pop: dict[tuple[str, str, str, str], Fraction]
                         ) -> dict[tuple[str, str, str, str], Fraction]:
    """z-score inside (family, sex), mapped back onto the family's own scale."""
    sc = scales(pop)
    out = {}
    for key, score in pop.items():
        family, sex = key[0], key[1]
        cell, grand = sc[(family, sex)], sc[(family, "*")]
        out[key] = grand.mean + grand.sd * (score - cell.mean) / cell.sd
    return out


def normalized_gaps(verdicts: list[dict]) -> dict[str, dict[str, Fraction]]:
    """pairing_id -> family -> normalized(woman) - normalized(man).

    Built from the two absolute scores, which is the only way a within-sex
    normalization can reach the gap at all: a gap has no sex of its own.
    """
    pop = population(observations(verdicts))
    norm = normalize_population(pop)
    out: dict[str, dict[str, Fraction]] = {}
    for v in verdicts:
        if v.get("f_absolute") is None or v.get("m_absolute") is None:
            continue
        fam, period = v["family"], str(v["period"])
        f = norm[(fam, "female", v["female_qid"], period)]
        m = norm[(fam, "male", v["male_qid"], period)]
        out.setdefault(v["pairing_id"], {})[fam] = f - m
    return out


def normalized_records(records: list[dict], verdicts: list[dict]
                       ) -> tuple[list[dict], dict]:
    """Board-ready records whose `gap` is the normalized gap.

    Everything else about a record is untouched, centrality most of all: it is
    a weight, not a score, and it has no sex-specific scale to remove.

    Families are reduced by the mean across the families that judged the
    pairing, which is the rule `merge_families` already uses for raw gaps.

    A record that carries a raw gap but reaches no normalized one is NOT
    silently dropped: it is counted and named in the returned diagnostics, and
    its gap is set to None so it leaves the board visibly rather than by
    arriving at some default.
    """
    gaps = normalized_gaps(verdicts)
    out, uncovered = [], []
    for r in records:
        g = gaps.get(r["pairing_id"])
        rec = dict(r)
        if g:
            vals = list(g.values())
            rec["gap"] = float(_mean(vals))
            rec["normalized_family_gaps"] = {k: float(v) for k, v in g.items()}
        else:
            if r.get("gap") is not None:
                uncovered.append(r["pairing_id"])
            rec["gap"] = None
            rec["normalized_family_gaps"] = {}
        out.append(rec)
    diag = {
        "pairings_normalized": sum(1 for r in out if r["gap"] is not None),
        "pairings_with_a_raw_gap_but_no_normalized_gap": len(uncovered),
        "uncovered_pairing_ids": sorted(uncovered),
        "observations": len(population(observations(verdicts))),
        "scales": [s.as_dict() for s in
                   scales(population(observations(verdicts))).values()],
    }
    return out, diag


def load_raw_verdicts(raw_dir: Path, records: list[dict]) -> list[dict]:
    """Read every stored verdict, joined to the pairing record for its metadata.

    The absolute scores live ONLY here. `pairing_scores.json` keeps the gap and
    the centrality and drops `f_absolute` and `m_absolute`, so a within-sex
    normalization cannot be built from the scored artifact at all.

    Parsing goes through `parse_pairing_verdict`, never `json.loads`. One of
    the two families wraps its JSON in a ```json fence, and 72 of the 262
    stored files are wrapped that way: a bare `json.loads` reads 190 of them,
    raises nothing, and reports a corpus a third smaller than the real one.
    """
    by_id = {r["pairing_id"]: r for r in records}
    out: list[dict] = []
    for f in sorted(Path(raw_dir).glob("*.txt")):
        m = _RAW_NAME.match(f.stem)
        if not m:
            raise NotNormalizable(
                f"{f.name} is not named <pairing_id>__<family>.txt, so the "
                f"judge family that produced it is unknown.")
        pid, family = m.group("pid"), m.group("family")
        try:
            v = parse_pairing_verdict(f.read_text(), pid)
        except ParseError as exc:
            raise NotNormalizable(f"{f.name}: {exc}") from exc
        if not v.judged or v.f_absolute is None or v.m_absolute is None:
            continue
        rec = by_id.get(pid)
        if rec is None:
            raise NotNormalizable(
                f"{f.name} holds a verdict for pairing {pid!r}, which is in no "
                f"scored artifact. Its sex, period and domain are unknown, so "
                f"it cannot be placed in a population.")
        out.append({
            "family": family, "pairing_id": pid,
            "male_qid": rec["male_qid"], "female_qid": rec["female_qid"],
            "period": str(rec["period"]), "domain": rec.get("domain"),
            "f_absolute": v.f_absolute, "m_absolute": v.m_absolute,
            "gap": v.gap,
        })
    return out


def rank_changes(before: list[dict], after: list[dict]) -> dict:
    """What normalization DID to one board's ordering.

    `moved` counts people whose rank number changed at all. `discordant_pairs`
    counts pairs of people whose relative order flipped, which is the quantity
    that does not inflate when one person moves and pushes everybody below them
    down by one.

    Membership is reported rather than assumed: a person present in one
    ordering and not the other is listed, never quietly matched to nothing.
    """
    b = [r["name"] for r in before]
    a = [r["name"] for r in after]
    common = set(b) & set(a)
    bc = [n for n in b if n in common]
    ac = [n for n in a if n in common]
    bpos = {n: i for i, n in enumerate(bc)}
    apos = {n: i for i, n in enumerate(ac)}
    moved = [(n, bpos[n] + 1, apos[n] + 1) for n in bc if bpos[n] != apos[n]]
    discordant = sum(
        1 for i, x in enumerate(bc) for y in bc[i + 1:]
        if (apos[x] > apos[y])
    )
    return {
        "people": len(common),
        "moved": len(moved),
        "discordant_pairs": discordant,
        "pairs": len(bc) * (len(bc) - 1) // 2,
        "movements": [list(m) for m in moved],
        "entered": sorted(n for n in a if n not in common),
        "left": sorted(n for n in b if n not in common),
        "before": b, "after": a,
    }
