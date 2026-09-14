#!/usr/bin/env python3
"""Derive the outside-roster partner universe from the scorable episodes.

This existed only as an inline snippet run by hand, which meant a clean clone
could not reproduce it and fetch_observations silently skipped partner matching
without saying so. A stage that some clones have and others do not is exactly
the kind of thing that makes two runs disagree for no visible reason.

Read-only. Spends no model quota.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402
from modules.records.wikidata import fetch_gender  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", default="data/pilot/records/episodes.json")
    ap.add_argument("--cohort", default="docs/pilot-cohort.json")
    ap.add_argument("--out", default="data/pilot/records/partner_universe.json")
    args = ap.parse_args()

    eps = require(REPO, args.episodes)
    roster = {p["wikidata_qid"] for p in require(REPO, args.cohort)["people"]}

    partners: dict[str, str] = {}
    for ep in eps["episodes"]:
        if ep["scorable"] and ep["partner_qid"] not in roster:
            partners[ep["partner_qid"]] = ep["partner_label"]

    genders = fetch_gender(sorted(partners)) if partners else {}
    unsourced = [q for q in partners if q not in genders]

    payload = {
        "gender_source": "wikidata P21 (sex or gender), sourced, never inferred",
        "gender_unsourced_count": len(unsourced),
        "note": (
            "Outside-roster partners appearing in scorable episodes. Public "
            "figures only; scripts/partner_eligibility.py splits those with no "
            "evidence FOUND from those this project must never rate."
        ),
        "gender_caveat": (
            "gender_category comes from Wikidata P21 and is a SOURCED "
            "public-identity field. It is never inferred from appearance and "
            "never from who somebody dated. A partner Wikidata does not record "
            "stays 'unknown' rather than being defaulted, and an unknown must "
            "keep that person out of a gendered view rather than into a guess."
        ),
        "derived_from": args.episodes,
        "people": [
            {"display_name": n, "wikidata_qid": q,
             "gender_category": genders.get(q, "unknown"),
             "cohort_note": "partner universe"}
            for q, n in sorted(partners.items(), key=lambda kv: kv[1])
        ],
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"outside-roster partners: {len(partners)}")
    from collections import Counter
    print(f"gender: {dict(Counter(genders.get(q, 'unknown') for q in partners))}")
    if unsourced:
        print(f"unsourced (left 'unknown', not guessed): "
              f"{[partners[q] for q in unsourced]}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
