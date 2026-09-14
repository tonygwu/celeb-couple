#!/usr/bin/env python3
"""Build attractiveness observations from permitted routes only.

Permitted route used here: English Wikipedia's own tables (CC BY-SA), which
report the fact of an award without touching the publisher's site. See
modules/consensus/wikipedia_lists for why that distinction is load-bearing.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from modules.consensus.wikipedia_lists import (  # noqa: E402
    fetch_section_wikitext, parse_award_table, to_records,
)

SOURCES = [
    {
        "page": "People (magazine)", "section": 4, "section_title": "Sexiest Man Alive",
        "publisher": "PEOPLE", "award_name": "Sexiest Man Alive",
        "candidate_pool": "men in entertainment and public life, chosen editorially by the magazine",
        "url": "https://en.wikipedia.org/wiki/People_(magazine)#Sexiest_Man_Alive",
        "gender_served": "male",
    },
    {
        "page": "Maxim (magazine)", "section": 6, "section_title": "Maxim Hot 100",
        "publisher": "Maxim", "award_name": "Maxim Hot 100 number one",
        "candidate_pool": "women in entertainment, chosen by the magazine; only the number one is reported here",
        "url": "https://en.wikipedia.org/wiki/Maxim_(magazine)#Maxim_Hot_100",
        "gender_served": "female",
    },
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default="docs/pilot-cohort.json")
    ap.add_argument("--out", default="data/pilot/observations")
    args = ap.parse_args()

    cohort = json.loads((REPO / args.cohort).read_text())
    name_to_person = {p["display_name"]: p["wikidata_qid"] for p in cohort["people"]}
    gender = {p["wikidata_qid"]: p["gender_category"] for p in cohort["people"]}
    now = datetime.now(timezone.utc).isoformat()

    all_editions, all_obs, source_notes = [], [], []
    for src in SOURCES:
        wikitext, sha = fetch_section_wikitext(src["page"], src["section"])
        rows = parse_award_table(wikitext)
        editions, obs = to_records(
            rows, page=src["page"], section_title=src["section_title"],
            publisher=src["publisher"], award_name=src["award_name"],
            candidate_pool=src["candidate_pool"], source_url=src["url"],
            content_hash=sha, retrieved_at_utc=now, name_to_person=name_to_person,
        )
        all_editions += editions
        all_obs += obs
        source_notes.append({
            "publisher": src["publisher"], "award": src["award_name"],
            "gender_served": src["gender_served"], "route": "wikipedia-api",
            "winner_rows_parsed": len(rows),
            "years": [rows[0].year, rows[-1].year] if rows else [],
            "observations_for_cohort": len(obs),
            "content_sha256": sha,
        })
        print(f"{src['award_name']:28} rows={len(rows):3} "
              f"cohort hits={len(obs)}  years={rows[0].year}-{rows[-1].year}")

    per_person = Counter(o.person_id for o in all_obs)
    by_gender = Counter(gender.get(o.person_id, "?") for o in all_obs)
    people_with = {o.person_id for o in all_obs}

    out = REPO / args.out
    out.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_utc": now,
        "route_note": (
            "Facts read from English Wikipedia (CC BY-SA), not from the publishers' "
            "sites. people.com and askmen.com forbid LLM extraction and dataset "
            "creation in their terms; maxim.com blocks the AI crawlers. Those routes "
            "were not used."
        ),
        "sources": source_notes,
        "editions": [
            {"list_edition_id": e.list_edition_id, "publisher": e.publisher,
             "title": e.title, "published_at": e.published_at.value,
             "published_precision": e.published_at.precision.value,
             "concerns_period": e.concerns_period.value,
             "candidate_set_described": e.candidate_set_described,
             "list_length": e.list_length, "attribution": e.attribution,
             "content_sha256": e.content_sha256}
            for e in all_editions
        ],
        "observations": [
            {"observation_id": o.observation_id, "person_id": o.person_id,
             "list_edition_id": o.list_edition_id,
             "evidence_type": o.evidence_type.value, "observed": o.observed,
             "concerns_period": o.concerns_period.value,
             "published_at": o.published_at.value,
             "excerpt": o.excerpt, "excerpt_locator": o.excerpt_locator,
             "lineage": {"original_source": o.lineage.original_source,
                         "is_syndicated_copy": o.lineage.is_syndicated_copy},
             "review_status": o.review_status}
            for o in all_obs
        ],
        "coverage": {
            "total_observations": len(all_obs),
            "cohort_people_with_any_observation": len(people_with),
            "cohort_people_total": len(cohort["people"]),
            "by_gender": dict(by_gender),
            "per_person": {k: v for k, v in per_person.most_common()},
            "people_with_none": sorted(
                p["display_name"] for p in cohort["people"]
                if p["wikidata_qid"] not in people_with
            ),
        },
    }
    (out / "observations.json").write_text(json.dumps(payload, indent=2))

    names = {p["wikidata_qid"]: p["display_name"] for p in cohort["people"]}
    print("\nobservations per cohort member:")
    for qid, n in per_person.most_common():
        print(f"  {names.get(qid, qid):22} {gender.get(qid,'?'):7} {n}")
    print("\nno observations at all:")
    for n in payload["coverage"]["people_with_none"]:
        print(f"  {n}")
    print(f"\nby gender: {dict(by_gender)}")
    print(f"wrote {out / 'observations.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
