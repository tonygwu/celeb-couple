#!/usr/bin/env python3
"""What would a source have to look like to make this product work?

"Find better sources" is not a specification. This turns it into one by
simulating a HYPOTHETICAL annual ranked list over the REAL episode structure
and the REAL roster, and asking how many comparable, jointly covered pairings
come out the other side.

The simulation only ever asks "would this person-year have been covered". It
never invents a score, and nothing it produces enters the corpus.

Read-only. Spends no model quota.
"""
from __future__ import annotations
import argparse, json, random, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402
from modules.consensus.nearby import resolve_period  # noqa: E402

#: A real annual list covers a slice of the eligible population, and the same
#: well-known names recur. Modelled as: each year the list names `names_per_year`
#: people drawn from the roster, weighted so prominent names recur.
SEED = 20260914


def _weighted_sample_without_replacement(pool, weights, k, rng):
    """``k`` DISTINCT names, drawn with the given weights.

    `rng.choices` samples WITH replacement, and `set(picks)` then collapsed the
    duplicates -- so a rung labelled "100 names per year" actually listed a
    median of 48 distinct people, and no rung above it listed more. The curve's
    saturation was therefore partly an artifact of the sampler rather than a
    property of the coverage problem.

    A published annual ranked list of 100 names contains 100 distinct people.
    Efraimidis-Spirakis gives exactly that: key each item by U^(1/w) and take
    the top k, which is weighted sampling without replacement.
    """
    if k >= len(pool):
        return list(pool)
    keys = {q: rng.random() ** (1.0 / weights[q]) for q in pool}
    return sorted(pool, key=lambda q: keys[q], reverse=True)[:k]


def simulate(episodes, roster_qids, *, names_per_year: int, first_year: int,
             last_year: int, bound: int, trials: int, rng: random.Random) -> dict:
    covered_counts = []
    for _ in range(trials):
        # a stable popularity ordering, so the same faces recur across years
        order = list(roster_qids)
        rng.shuffle(order)
        weights = {q: 1.0 / (i + 3) for i, q in enumerate(order)}
        listed: dict[str, dict[str, float]] = {}
        pool = list(weights)
        for year in range(first_year, last_year + 1):
            picks = _weighted_sample_without_replacement(
                pool, weights, names_per_year, rng)
            for q in picks:
                listed.setdefault(q, {})[str(year)] = 1.0
        covered = 0
        for e in episodes:
            a, b = e["subject_qid"], e["partner_qid"]
            if a not in listed or b not in listed:
                continue
            for y in [str(v) for v in e.get("adult_years", [])]:
                ra = resolve_period(y, listed.get(a, {}), bound)
                rb = resolve_period(y, listed.get(b, {}), bound)
                if ra.scored and rb.scored:
                    covered += 1
                    break
        covered_counts.append(covered)
    covered_counts.sort()
    n = len(covered_counts)
    return {"names_per_year": names_per_year,
            "median_covered": covered_counts[n // 2],
            "p10": covered_counts[max(0, int(0.1 * n))],
            "p90": covered_counts[min(n - 1, int(0.9 * n))]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=120)
    ap.add_argument("--bound", type=int, default=1)
    ap.add_argument("--out", default="data/roster100/run/source_requirement.json")
    args = ap.parse_args()

    eps = require(REPO, "data/roster100/records/episodes.json")
    roster = require(REPO, "docs/roster-100.json")["people"]
    qids = [p["wikidata_qid"] for p in roster if p["wikidata_qid"]]
    scorable = [e for e in eps["episodes"] if e["scorable"] and e.get("adult_years")]
    years = [int(y) for e in scorable for y in e["adult_years"]]
    first, last = min(years), max(years)

    rng = random.Random(SEED)
    ladder = [1, 5, 10, 25, 50, 100, 200, 400]
    results = [simulate(scorable, qids, names_per_year=k, first_year=first,
                        last_year=last, bound=args.bound, trials=args.trials,
                        rng=rng)
               for k in ladder]

    payload = {
        "episodes_simulated": len(scorable),
        "roster": len(qids), "years": [first, last], "bound": args.bound,
        "trials_per_rung": args.trials, "seed": SEED,
        "model": ("One hypothetical annual list naming N people from the roster "
                  "each year, weighted so prominent names recur, across the full "
                  "period the episodes span. Coverage means both partners "
                  "resolvable within the bound in the same year."),
        "caveat": ("A simulation of COVERAGE only. It invents no score, and a "
                   "real list's pool would not be the roster. Read the shape of "
                   "the curve, not the absolute numbers."),
        "ladder": results,
    }
    (REPO / args.out).parent.mkdir(parents=True, exist_ok=True)
    (REPO / args.out).write_text(json.dumps(payload, indent=2))

    print(f"simulating {len(scorable)} scorable episodes, roster {len(qids)}, "
          f"years {first}-{last}, bound +/-{args.bound}, {args.trials} trials/rung\n")
    print("  names/year   episodes jointly covered (p10 / median / p90)")
    for r in results:
        print(f"  {r['names_per_year']:>9}   {r['p10']:>4} / {r['median_covered']:>4} "
              f"/ {r['p90']:>4}")
    print("\nreal sources for comparison:")
    print("   Sexiest Man Alive                  1 name/year")
    print("   People Most Beautiful cover        1 name/year")
    print("   Maxim Hot 100 (as published)       1 name/year")
    print("   FHM top ten (as on Wikipedia)     10 names/year")
    print("   FHM full list (NOT available)    100 names/year")
    print(f"\nwrote {REPO / args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
