#!/usr/bin/env python3
"""Measure evidence DENSITY: how many observations land on one person-period.

WHY THIS IS THE NUMBER THAT MATTERS
-----------------------------------
Coverage asks whether a person-year has any evidence. Density asks how much.
Measured 2026-09-14, the difference is the whole problem:

  - The synthetic stress corpus, whose dossiers carry one to five observations
    of varying shape, produced estimates spanning 63 to 92. The rubric
    discriminates across a 29-point range.
  - The real corpus produced 13 estimates spanning 86.5 to 92.0, and twelve of
    them were exactly 92.0.

The difference is not the rubric and not rater noise. Every single real
person-period carries exactly ONE observation, and a single one-winner award is
superlative by construction, so it can only land in one band.

So "find more sources" is not the requirement. The requirement is sources that
land on the SAME person-year as an existing one. A source that adds a hundred
new people at one observation each changes nothing about the board.

Read-only. Spends no model quota.
"""
from __future__ import annotations
import argparse, json, statistics, sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--observations", default="data/pilot/observations/observations.json")
    ap.add_argument("--scores", default="data/pilot/run/evidenced_scores.json")
    ap.add_argument("--stress", default="data/pilot/stress/stress_report.json")
    ap.add_argument("--out", default="data/pilot/run/evidence_density.json")
    args = ap.parse_args()

    obs = json.loads((REPO / args.observations).read_text())
    editions = {e["list_edition_id"]: e for e in obs["editions"]}

    per_pp: dict[tuple[str, str], list[dict]] = {}
    for o in obs["observations"]:
        per_pp.setdefault((o["person_id"], o["concerns_period"]), []).append(o)

    counts = Counter(len(v) for v in per_pp.values())
    shapes = Counter(o["evidence_type"] for o in obs["observations"])
    # a person-period is only informative if it can distinguish bands, which
    # needs either several observations or one that is not a bare award
    singleton_award = sum(
        1 for v in per_pp.values()
        if len(v) == 1 and v[0]["evidence_type"] == "editorial_award"
    )
    # Publisher names arrive with inconsistent case from different routes
    # ("PEOPLE" from a table title, "People" from prose), and comparing them raw
    # reported one magazine as two independent publishers.
    multi_publisher = sum(
        1 for v in per_pp.values()
        if len({(editions[o["list_edition_id"]]["publisher"] or "").strip().lower()
                for o in v}) > 1
    )

    real_spread = None
    if (REPO / args.scores).exists():
        sc = json.loads((REPO / args.scores).read_text())
        vals = [r["estimate"] for r in sc["person_periods"] if r["estimate"] is not None]
        if vals:
            real_spread = {"n": len(vals), "min": min(vals), "max": max(vals),
                           "range": round(max(vals) - min(vals), 3),
                           "distinct_values": len(set(vals)),
                           "sd": round(statistics.pstdev(vals), 3)}

    synthetic_spread = None
    if (REPO / args.stress).exists():
        st = json.loads((REPO / args.stress).read_text())
        vals = [r["estimate"] for r in st["results"] if r["scored"]]
        if vals:
            synthetic_spread = {"n": len(vals), "min": min(vals), "max": max(vals),
                                "range": max(vals) - min(vals),
                                "distinct_values": len(set(vals)),
                                "sd": round(statistics.pstdev(vals), 3)}

    payload = {
        "person_periods": len(per_pp),
        "observations": len(obs["observations"]),
        "mean_observations_per_person_period": round(
            len(obs["observations"]) / len(per_pp), 3) if per_pp else 0,
        "distribution": {str(k): v for k, v in sorted(counts.items())},
        "person_periods_with_one_observation": counts.get(1, 0),
        "person_periods_that_are_a_lone_award": singleton_award,
        "person_periods_with_two_or_more_publishers": multi_publisher,
        "observation_shapes": dict(shapes),
        "real_estimate_spread": real_spread,
        "synthetic_estimate_spread": synthetic_spread,
        "reading": (
            "The rubric discriminates; the corpus does not let it. A lone "
            "one-winner award is superlative by construction and can only land "
            "in one band, so a person-period carrying exactly that produces the "
            "same number every time. What the board needs is not more sources "
            "covering more people, but sources landing on the SAME person-year "
            "as an existing observation."
        ),
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))

    print(f"person-periods: {payload['person_periods']}  "
          f"observations: {payload['observations']}  "
          f"mean density: {payload['mean_observations_per_person_period']}")
    print(f"distribution (observations per person-period): {payload['distribution']}")
    print(f"lone-award person-periods: {singleton_award} of {len(per_pp)}")
    print(f"person-periods with 2+ publishers: {multi_publisher}")
    print(f"shapes: {dict(shapes)}")
    if real_spread and synthetic_spread:
        print(f"\nreal estimates      n={real_spread['n']:2} range {real_spread['range']:5} "
              f"distinct {real_spread['distinct_values']} sd {real_spread['sd']}")
        print(f"synthetic estimates n={synthetic_spread['n']:2} range "
              f"{synthetic_spread['range']:5} distinct "
              f"{synthetic_spread['distinct_values']} sd {synthetic_spread['sd']}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
