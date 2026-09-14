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
from packages.llmkit.artifacts import require  # noqa: E402
from modules.analytics.comparability import classify_pairing            # noqa: E402
from modules.consensus.nearby import NEARBY_BOUND_YEARS, resolve_period  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bound", type=int, default=NEARBY_BOUND_YEARS)
    ap.add_argument("--out", default="data/pilot/run/joint_with_nearby.json")
    args = ap.parse_args()

    obs = require(REPO, "data/pilot/observations/observations.json")
    eps = require(REPO, "data/pilot/records/episodes.json")
    films = require(REPO, "data/pilot/records/onscreen_candidates.json")
    romance_path = REPO / "data/pilot/records/romance.json"
    romance = (json.loads(romance_path.read_text()) if romance_path.exists() else None)
    cohort = json.loads((REPO / "docs/pilot-cohort.json").read_text())
    names = {p["wikidata_qid"]: p["display_name"] for p in cohort["people"]}

    # A film pairing counts only when the romance classifier confirmed a
    # reciprocal, grounded romance. Co-appearance in a cast list is not a
    # pairing, and until this filter existed the coverage number counted Being
    # John Malkovich as a Brad Pitt / Michelle Pfeiffer couple.
    qualifying: set[tuple[str, str, str]] | None = None
    romance_by_key: dict[tuple[str, str, str], str] = {}
    if romance:
        qualifying = set()
        for c in romance["candidates"]:
            key = (c["work_qid"], c["male_qid"], c["female_qid"])
            romance_by_key[key] = c.get("classification") or "unclassified"
            if c.get("qualifies"):
                qualifying.add(key)

    have: dict[str, dict[str, float]] = {}
    shape_of: dict[tuple[str, str], set[str]] = {}
    for o in obs["observations"]:
        have.setdefault(o["person_id"], {})[o["concerns_period"]] = 1.0
        shape_of.setdefault((o["person_id"], o["concerns_period"]), set()).add(
            o["evidence_type"])

    def _shape(pid: str, period: str | None) -> str | None:
        if period is None:
            return None
        shapes = shape_of.get((pid, period))
        return "+".join(sorted(shapes)) if shapes else None

    joint, near_misses = [], []

    excluded_by_romance = 0
    for c in films["candidates"]:
        a, b, y = c["male_qid"], c["female_qid"], c["release"][:4]
        if not y.isdigit():
            continue
        key = (c["work_qid"], a, b)
        if qualifying is not None and key not in qualifying:
            excluded_by_romance += 1
            continue
        ra = resolve_period(y, have.get(a, {}), args.bound)
        rb = resolve_period(y, have.get(b, {}), args.bound)
        row = {"domain": "on_screen", "work": c["title"], "period": y,
               "a": c["male"], "a_qid": a, "b": c["female"], "b_qid": b,
               "a_src": ra.source_period, "a_dist": ra.distance, "a_support": ra.support,
               "b_src": rb.source_period, "b_dist": rb.distance, "b_support": rb.support,
               "romance_classification": romance_by_key.get(key, "unclassified"),
               "verification": ("reciprocal romance confirmed from the plot text"
                                if qualifying is not None
                                else "co-appearance only; ROMANCE UNVERIFIED")}
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

    # Label each jointly covered row: is this gap comparing two people, or two
    # publication formats? a large share of the estimate is evidence shape.
    for j in joint:
        c = classify_pairing(
            f"{j['domain']}_{j['period']}_{j['a_qid']}_{j['b_qid']}",
            _shape(j["a_qid"], j["a_src"]), _shape(j["b_qid"], j["b_src"]))
        j["comparability"] = c.status
        j["a_shape"], j["b_shape"] = c.a_shape, c.b_shape
        if c.caveat:
            j["comparability_caveat"] = c.caveat

    distinct = {(j["a_qid"], j["b_qid"], j["work"]) for j in joint}
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "bound_years": args.bound,
        "note": ("Both sides resolved within the bound. Any entry with distance 1 "
                 "is a REUSED estimate flagged nearby_period, and must share one "
                 "draw with every other period that same estimate serves."),
        "romance_filter_applied": qualifying is not None,
        "denominators": {
            "episodes_examined": len(eps["episodes"]),
            "films_examined": len(films["candidates"]),
            "films_excluded_as_not_a_romance": excluded_by_romance,
            "films_qualifying_as_romance": (
                len(qualifying) if qualifying is not None else None),
            "candidate_pairings": len(eps["episodes"]) + len(films["candidates"]),
        },
        "jointly_covered_pairing_periods": len(joint),
        "comparability": {
            k: sum(1 for j in joint if j.get("comparability") == k)
            for k in ("comparable", "shape_mismatched", "shape_unknown")
        },
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
    if qualifying is not None:
        print(f"films excluded as not a romance: {excluded_by_romance} "
              f"(of {len(films['candidates'])}); qualifying: {len(qualifying)}")
    print(f"jointly covered pairing-periods: {len(joint)}  "
          f"(distinct pairings: {len(distinct)})")
    print(f"comparability: {payload['comparability']}")
    for j in joint:
        flag = "" if j.get("comparability") == "comparable" else f"  [{j.get('comparability')}]"
        print(f"  {j['domain']:10} {j['period']}  {(j['work'] or '(relationship)')[:32]:32} "
              f"{j['a'][:16]:16} (from {j['a_src']}, d={j['a_dist']}) + "
              f"{j['b'][:16]:16} (from {j['b_src']}, d={j['b_dist']}){flag}")
    print(f"\none-sided film pairings (exactly one side scorable): {len(near_misses)}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
