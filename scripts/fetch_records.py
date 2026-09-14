#!/usr/bin/env python3
"""Fetch relationship candidates and birth dates for the pilot cohort.

Read-only against Wikidata (CC0). Writes candidates, never accepted records:
every one carries review_status "pending" until a human reviews it.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from modules.records.wikidata import fetch_birth_dates, fetch_relationships  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default="docs/pilot-cohort.json")
    ap.add_argument("--out", default="data/pilot/records")
    args = ap.parse_args()

    cohort = json.loads((REPO / args.cohort).read_text())
    qids = [p["wikidata_qid"] for p in cohort["people"] if p.get("wikidata_qid")]
    by_qid = {p["wikidata_qid"]: p for p in cohort["people"]}

    print(f"cohort: {len(qids)} people")
    candidates = fetch_relationships(qids)
    births = fetch_birth_dates(qids)
    partner_qids = sorted({c.partner_qid for c in candidates})
    partner_births = fetch_birth_dates(partner_qids) if partner_qids else {}

    out = Path(REPO / args.out)
    out.mkdir(parents=True, exist_ok=True)

    by_subject: dict[str, list] = {}
    for c in candidates:
        by_subject.setdefault(c.subject_qid, []).append(c)

    print("\nrelationship candidates (UNVERIFIED, pending review):")
    for qid in qids:
        rows = by_subject.get(qid, [])
        name = by_qid[qid]["display_name"]
        print(f"  {name:22} {len(rows):2} candidates")
        for c in rows:
            s = f"{c.start.value}({c.start.precision.value[0]})" if c.start else "?"
            e = f"{c.end.value}({c.end.precision.value[0]})" if c.end else "ongoing/unknown"
            print(f"       {c.relation:18} {c.partner_label[:28]:28} {s:12} -> {e:18} ref={'Y' if c.has_reference else 'N'}")

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "wikidata",
        "licence": "CC0",
        "caveat": (
            "CANDIDATES ONLY. Wikidata is incomplete: a probe of four subjects on "
            "2026-09-13 returned 13 episodes and missed a widely reported earlier "
            "engagement for one and an eight-year relationship for another. "
            "Nothing here is an accepted record until reviewed."
        ),
        "cohort_version": cohort["version"],
        "birth_dates": {
            q: {"value": d.value, "precision": d.precision.value}
            for q, d in {**births, **partner_births}.items()
        },
        "candidates": [c.as_dict() for c in candidates],
        "counts": {
            "subjects": len(qids),
            "candidates": len(candidates),
            "distinct_partners": len(partner_qids),
            "with_reference": sum(1 for c in candidates if c.has_reference),
            "with_start_date": sum(1 for c in candidates if c.start),
            "with_end_date": sum(1 for c in candidates if c.end),
            "start_year_precision_only": sum(
                1 for c in candidates if c.start and c.start.precision.value == "year"
            ),
            "birth_dates_found": len({**births, **partner_births}),
        },
    }
    (out / "relationship_candidates.json").write_text(json.dumps(payload, indent=2))
    print("\ncounts:", json.dumps(payload["counts"], indent=2))
    print(f"wrote {out / 'relationship_candidates.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
