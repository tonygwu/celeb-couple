#!/usr/bin/env python3
"""Joint pairing-period coverage: are BOTH sides scorable over the same period?

This is the number that decides whether a pairing contributes anything. A
pairing with one side unscored is removed from BOTH mirrored gender views, so
person-period availability on its own says nothing about whether a board is
possible.

Read-only. Spends no model quota: it asks whether evidence EXISTS, not what it
is worth.
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from modules.consensus.nearby import NEARBY_BOUND_YEARS, resolve_period  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bound", type=int, default=NEARBY_BOUND_YEARS)
    ap.add_argument("--out", default="data/pilot/run/joint_with_nearby.json")
    args = ap.parse_args()

    obs = json.loads((REPO / "data/pilot/observations/observations.json").read_text())
    eps = json.loads((REPO / "data/pilot/records/episodes.json").read_text())
    films = json.loads((REPO / "data/pilot/records/onscreen_candidates.json").read_text())
    cohort = json.loads((REPO / "docs/pilot-cohort.json").read_text())
    names = {p["wikidata_qid"]: p["display_name"] for p in cohort["people"]}

    have: dict[str, dict[str, float]] = {}
    for o in obs["observations"]:
        have.setdefault(o["person_id"], {})[o["concerns_period"]] = 1.0

    joint, near_misses = [], []

    for c in films["candidates"]:
        a, b, y = c["male_qid"], c["female_qid"], c["release"][:4]
        if not y.isdigit():
            continue
        ra = resolve_period(y, have.get(a, {}), args.bound)
        rb = resolve_period(y, have.get(b, {}), args.bound)
        row = {"domain": "on_screen", "work": c["title"], "period": y,
               "a": c["male"], "a_qid": a, "b": c["female"], "b_qid": b,
               "a_src": ra.source_period, "a_dist": ra.distance, "a_support": ra.support,
               "b_src": rb.source_period, "b_dist": rb.distance, "b_support": rb.support,
               "verification": "co-appearance only; ROMANCE UNVERIFIED"}
        if ra.scored and rb.scored:
            joint.append(row)
        elif ra.scored or rb.scored:
            near_misses.append({**row, "missing_side": "b" if ra.scored else "a"})

    for e in eps["episodes"]:
        a, b = e["subject_qid"], e["partner_qid"]
        for y in [str(v) for v in e.get("adult_years", [])]:
            ra = resolve_period(y, have.get(a, {}), args.bound)
            rb = resolve_period(y, have.get(b, {}), args.bound)
            if ra.scored and rb.scored:
                joint.append({"domain": "real_life", "work": None, "period": y,
                              "a": names.get(a, a), "a_qid": a,
                              "b": e["partner_label"], "b_qid": b,
                              "a_src": ra.source_period, "a_dist": ra.distance,
                              "a_support": ra.support, "b_src": rb.source_period,
                              "b_dist": rb.distance, "b_support": rb.support,
                              "verification": "wikidata candidate; UNVERIFIED"})

    distinct = {(j["a_qid"], j["b_qid"], j["work"]) for j in joint}
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "bound_years": args.bound,
        "note": ("Both sides resolved within the bound. Any entry with distance 1 "
                 "is a REUSED estimate flagged nearby_period, and must share one "
                 "draw with every other period that same estimate serves."),
        "denominators": {
            "episodes_examined": len(eps["episodes"]),
            "films_examined": len(films["candidates"]),
            "candidate_pairings": len(eps["episodes"]) + len(films["candidates"]),
        },
        "jointly_covered_pairing_periods": len(joint),
        "distinct_jointly_covered_pairings": len(distinct),
        "one_sided_film_pairings": len(near_misses),
        "jointly_covered": joint,
        "near_misses": near_misses,
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))

    print(f"bound = +/-{args.bound} year(s)")
    print(f"candidate pairings examined: {payload['denominators']['candidate_pairings']}")
    print(f"jointly covered pairing-periods: {len(joint)}  "
          f"(distinct pairings: {len(distinct)})")
    for j in joint:
        print(f"  {j['domain']:10} {j['period']}  {(j['work'] or '(relationship)')[:32]:32} "
              f"{j['a'][:16]:16} (from {j['a_src']}, d={j['a_dist']}) + "
              f"{j['b'][:16]:16} (from {j['b_src']}, d={j['b_dist']})")
    print(f"\none-sided film pairings (exactly one side scorable): {len(near_misses)}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
