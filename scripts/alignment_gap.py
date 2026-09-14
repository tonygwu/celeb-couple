#!/usr/bin/env python3
"""For each candidate pairing, what nearby-period bound would it take to score?

Joint coverage stayed at 1 of 51 while the corpus grew from 13 observations to
25. That says the binding constraint is not evidence VOLUME but temporal
ALIGNMENT: both people need a judgment near the same year, and having more
judgments in unrelated years does not help.

This quantifies the cost of the +/-1 bound by asking, per pairing, the smallest
bound that would make both sides resolvable. It does NOT recommend widening the
bound. A wider bound reuses an estimate further from the period it describes,
which is exactly the manufactured precision the bound exists to prevent. The
point is to know what the rule costs before anybody argues about it.

Read-only. Spends no model quota.
"""
from __future__ import annotations
import argparse, json, sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402
from modules.consensus.nearby import NEARBY_BOUND_YEARS  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-bound", type=int, default=12)
    ap.add_argument("--out", default="data/pilot/run/alignment_gap.json")
    args = ap.parse_args()

    obs = require(REPO, "data/pilot/observations/observations.json")
    eps = require(REPO, "data/pilot/records/episodes.json")
    films = require(REPO, "data/pilot/records/onscreen_candidates.json")
    rom = require(REPO, "data/pilot/records/romance.json")
    cohort = json.loads((REPO / "docs/pilot-cohort.json").read_text())
    names = {p["wikidata_qid"]: p["display_name"] for p in cohort["people"]}

    years: dict[str, set[int]] = {}
    for o in obs["observations"]:
        try:
            years.setdefault(o["person_id"], set()).add(int(o["concerns_period"]))
        except ValueError:
            pass
    qualifying = {(c["work_qid"], c["male_qid"], c["female_qid"])
                  for c in rom["candidates"] if c.get("qualifies")}

    def min_bound(a: str, b: str, periods: list[int]) -> int | None:
        ya, yb = years.get(a, set()), years.get(b, set())
        if not ya or not yb or not periods:
            return None
        best = None
        for p in periods:
            d = max(min((abs(p - y) for y in ya), default=10**6),
                    min((abs(p - y) for y in yb), default=10**6))
            best = d if best is None else min(best, d)
        return best

    rows = []
    for c in films["candidates"]:
        y = c["release"][:4]
        if not y.isdigit():
            continue
        if (c["work_qid"], c["male_qid"], c["female_qid"]) not in qualifying:
            continue
        mb = min_bound(c["male_qid"], c["female_qid"], [int(y)])
        rows.append({"domain": "on_screen", "label": f"{c['title']} ({y})",
                     "a": c["male"], "b": c["female"], "min_bound": mb,
                     "a_years": sorted(years.get(c["male_qid"], [])),
                     "b_years": sorted(years.get(c["female_qid"], []))})
    for e in eps["episodes"]:
        if not e["scorable"] or not e.get("adult_years"):
            continue
        mb = min_bound(e["subject_qid"], e["partner_qid"],
                       [int(v) for v in e["adult_years"]])
        rows.append({"domain": "real_life",
                     "label": f"{e['subject_name']} + {e['partner_label']}",
                     "a": e["subject_name"], "b": e["partner_label"], "min_bound": mb,
                     "a_years": sorted(years.get(e["subject_qid"], [])),
                     "b_years": sorted(years.get(e["partner_qid"], []))})

    resolvable = [r for r in rows if r["min_bound"] is not None]
    hist = Counter(r["min_bound"] for r in resolvable)
    cumulative = {}
    for b in range(0, args.max_bound + 1):
        cumulative[b] = sum(v for k, v in hist.items() if k <= b)

    payload = {
        "pairings_considered": len(rows),
        "pairings_with_evidence_on_both_sides": len(resolvable),
        "pairings_with_no_evidence_on_one_or_both_sides": len(rows) - len(resolvable),
        "min_bound_histogram": {str(k): v for k, v in sorted(hist.items())},
        "jointly_covered_at_bound": cumulative,
        "current_bound": NEARBY_BOUND_YEARS,
        "reading": (
            "A pairing needs BOTH people judged near the same year. Growing the "
            "corpus from 13 observations to 25 did not move joint coverage, "
            "because the new judgments landed in years the pairings do not span. "
            "The binding constraint is temporal alignment, not volume."
        ),
        "caveat": (
            "This measures what the bound costs. It is NOT an argument for "
            "widening it: a wider bound reuses an estimate further from the "
            "period it is supposed to describe, which is the manufactured "
            "precision the bound exists to prevent."
        ),
        "pairings": sorted(resolvable, key=lambda r: r["min_bound"]),
        "unresolvable": [r["label"] for r in rows if r["min_bound"] is None],
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))

    print(f"pairings considered: {len(rows)}  "
          f"with evidence on both sides: {len(resolvable)}  "
          f"missing a side entirely: {len(rows) - len(resolvable)}")
    print("\njointly covered at each bound:")
    for b in range(0, min(args.max_bound, 10) + 1):
        # Was a literal 1. The declared bound lives in one place; a display
        # that hardcodes it labels the wrong row the day it changes.
        mark = "  <-- current" if b == NEARBY_BOUND_YEARS else ""
        print(f"   +/-{b:2}  {cumulative[b]:3}{mark}")
    print("\nclosest unmet pairings:")
    for r in payload["pairings"][:8]:
        if r["min_bound"] > NEARBY_BOUND_YEARS:
            print(f"   bound {r['min_bound']:2}  {r['label'][:44]:44} "
                  f"{r['a'][:16]} {r['a_years']} + {r['b'][:16]} {r['b_years']}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
