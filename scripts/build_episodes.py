#!/usr/bin/env python3
"""Merge relationship candidates into reviewable episodes and report coverage."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.temporal.dates import Precision, PreciseDate           # noqa: E402
from modules.records.episodes import adult_window, merge_progressions  # noqa: E402
from modules.records.wikidata import RelationshipCandidate           # noqa: E402


def _pd(blob, ref):
    if not blob:
        return None
    return PreciseDate(blob["value"], Precision(blob["precision"]), ref)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default="data/pilot/records/relationship_candidates.json")
    ap.add_argument("--cohort", default="docs/pilot-cohort.json")
    ap.add_argument("--as-of", default="2026-09-14")
    ap.add_argument("--out", default="data/pilot/records/episodes.json")
    args = ap.parse_args()

    blob = json.loads((REPO / args.records).read_text())
    cohort = json.loads((REPO / args.cohort).read_text())
    names = {p["wikidata_qid"]: p["display_name"] for p in cohort["people"]}
    births = {q: _pd(d, f"wikidata:{q}:P569") for q, d in blob["birth_dates"].items()}

    cands = [
        RelationshipCandidate(
            episode_id=c["episode_id"], pair_key=c["pair_key"],
            subject_qid=c["subject_qid"], partner_qid=c["partner_qid"],
            partner_label=c["partner_label"], relation=c["relation"],
            start=_pd(c["start"], c["episode_id"]), end=_pd(c["end"], c["episode_id"]),
            has_reference=c["has_reference"],
        )
        for c in blob["candidates"]
    ]
    # keep only the cohort member's side, so a couple inside the cohort is not
    # counted twice; the mirrored view is a presentation, not a second record
    cohort_qids = set(names)
    cands = [c for c in cands if c.subject_qid in cohort_qids]

    episodes = merge_progressions(cands)
    as_of = PreciseDate(args.as_of, Precision.DAY, "run:as_of")

    rows, defect_counts, exclusions = [], Counter(), Counter()
    for ep in episodes:
        row = ep.as_dict()
        row["subject_name"] = names.get(ep.subject_qid, ep.subject_qid)
        # A defective episode never gets an interval: Interval() refuses an end
        # that precedes its start, which is exactly the defect the fetch found.
        iv = ep.interval(as_of if ep.end is None else None) if ep.scorable else None
        adult_iv, reason = (None, None)
        if iv is not None:
            adult_iv, reason = adult_window(
                iv, births.get(ep.subject_qid), births.get(ep.partner_qid)
            )
        row["ongoing"] = ep.start is not None and ep.end is None
        row["adult_years"] = (
            sorted(adult_iv.year_shares()) if adult_iv is not None else []
        )
        row["adult_days"] = adult_iv.days() if adult_iv is not None else 0
        row["exclusion_reason"] = reason
        if reason:
            exclusions[reason] += 1
        for d in ep.defects:
            defect_counts[d.kind] += 1
        rows.append(row)

    eligible = [r for r in rows if r["scorable"] and not r["exclusion_reason"]]
    periods = sorted({y for r in eligible for y in r["adult_years"]})

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_as_of": args.as_of,
        "note": (
            "data_as_of closes an ongoing episode. It is NOT the render time and "
            "NOT a claim the relationship continued to that date."
        ),
        "counts": {
            "candidates_in": len(cands),
            "episodes_after_merge": len(episodes),
            "merged_progressions": sum(1 for r in rows if len(r["merged_from"]) > 1),
            "with_defects": sum(1 for r in rows if r["defects"]),
            "ongoing": sum(1 for r in rows if r["ongoing"]),
            "eligible_after_adult_window": len(eligible),
            "distinct_person_periods_needed": len(
                {(r["subject_qid"], y) for r in eligible for y in r["adult_years"]}
                | {(r["partner_qid"], y) for r in eligible for y in r["adult_years"]}
            ),
            "period_span": [periods[0], periods[-1]] if periods else [],
        },
        "defects": dict(defect_counts),
        "exclusions": dict(exclusions),
        "episodes": rows,
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    print(json.dumps(report["counts"], indent=2))
    print("defects:", json.dumps(report["defects"], indent=2))
    print("exclusions:", json.dumps(report["exclusions"], indent=2))
    print("\nmerged progressions:")
    for r in rows:
        if len(r["merged_from"]) > 1:
            print(f"  {r['subject_name']:20} + {r['partner_label'][:24]:24} "
                  f"{r['stages']} {r['start']['value']} -> {r['end']['value'] if r['end'] else '?'}")
    print("\nunscorable:")
    for r in rows:
        if r["defects"] or r["exclusion_reason"]:
            why = [d["kind"] for d in r["defects"]] + ([r["exclusion_reason"]] if r["exclusion_reason"] else [])
            print(f"  {r['subject_name']:20} + {r['partner_label'][:24]:24} {why}")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
