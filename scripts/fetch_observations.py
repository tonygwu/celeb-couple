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

from modules.consensus.ranked_lists import (  # noqa: E402
    parse_ranked_table, ranked_to_records,
)
from modules.consensus.wikipedia_lists import (  # noqa: E402
    fetch_section_wikitext, parse_award_table_with_stats, to_records,
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
    {
        "page": "People (magazine)", "section": 9,
        "section_title": "100 Most Beautiful People",
        "publisher": "PEOPLE", "award_name": "Most Beautiful cover choice",
        "candidate_pool": (
            "people worldwide, chosen editorially by the magazine for its annual "
            "Beautiful Issue cover; mixed gender, though mostly women"
        ),
        "url": "https://en.wikipedia.org/wiki/People_(magazine)#100_Most_Beautiful_People",
        "gender_served": "mixed",
    },
    {
        "page": "Esquire (magazine)", "section": 6,
        "section_title": "Sexiest Woman Alive",
        "publisher": "Esquire", "award_name": "Sexiest Woman Alive",
        "candidate_pool": "women in entertainment, chosen editorially by the magazine",
        "url": "https://en.wikipedia.org/wiki/Esquire_(magazine)#Sexiest_Woman_Alive",
        "gender_served": "female",
    },
]

#: Sources that publish an ORDERED ranking with depth, which is the shape M0
#: showed a one-winner award cannot supply.
RANKED_SOURCES = [
    {
        "page": "FHM's 100 Sexiest Women (UK)", "section": 2,
        "section_title": "100 Sexiest Women winners",
        "publisher": "FHM", "list_title": "FHM 100 Sexiest Women (UK)",
        "list_length": 100,
        "order_basis": (
            "the table publishes a winner and an explicitly numbered top ten "
            "('2nd:', '3rd:', ...) for each year"
        ),
        "candidate_pool": (
            "women in entertainment and modelling, reader-voted in a UK men's "
            "magazine; the readership skews British, so the pool is NOT the same "
            "pool as a US Hollywood list"
        ),
        "url": "https://en.wikipedia.org/wiki/FHM%27s_100_Sexiest_Women_(UK)",
        "gender_served": "female",
    },
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default="docs/pilot-cohort.json")
    ap.add_argument("--partners", default="data/pilot/records/partner_universe.json")
    ap.add_argument("--out", default="data/pilot/observations")
    args = ap.parse_args()

    cohort = json.loads((REPO / args.cohort).read_text())
    people = list(cohort["people"])
    # The partner universe must be matched too. Without it a list-article row
    # naming a partner is parsed and then DISCARDED, because the name map only
    # held the cohort. Jennifer Lopez is People's 2011 Most Beautiful cover
    # choice, that row was parsed on every run, and it was thrown away every
    # time -- while the partner-eligibility report listed her as a public figure
    # with no evidence found.
    partners_path = REPO / args.partners
    if partners_path.exists():
        people += json.loads(partners_path.read_text())["people"]
    seen = set()
    name_to_person, gender = {}, {}
    for p in people:
        if p["wikidata_qid"] in seen:
            continue
        seen.add(p["wikidata_qid"])
        name_to_person[p["display_name"]] = p["wikidata_qid"]
        gender[p["wikidata_qid"]] = p.get("gender_category", "unknown")
    now = datetime.now(timezone.utc).isoformat()

    all_editions, all_obs, source_notes = [], [], []
    for src in SOURCES:
        wikitext, sha = fetch_section_wikitext(src["page"], src["section"])
        rows, stats = parse_award_table_with_stats(wikitext)
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
            "table_rows_in_wikitext": stats.row_blocks,
            "rows_parsed": stats.parsed,
            "rows_skipped": stats.skipped,
            "skip_note": (
                "skipped rows carry no date cell (usually a rowspan continuation "
                "when one year names several people) or no wiki-link; they are "
                "dropped rather than guessed at"
            ) if stats.skipped else None,
        })
        print(f"{src['award_name']:30} parsed={len(rows):3} skipped={stats.skipped} "
              f"cohort hits={len(obs)}  years={rows[0].year}-{rows[-1].year}")

    for src in RANKED_SOURCES:
        wikitext, sha = fetch_section_wikitext(src["page"], src["section"])
        entries, stats = parse_ranked_table(wikitext, list_length=src["list_length"])
        editions, obs = ranked_to_records(
            entries, page=src["page"], section_title=src["section_title"],
            publisher=src["publisher"], list_title=src["list_title"],
            list_length=src["list_length"], order_basis=src["order_basis"],
            candidate_pool=src["candidate_pool"], source_url=src["url"],
            content_hash=sha, retrieved_at_utc=now, name_to_person=name_to_person,
        )
        all_editions += editions
        all_obs += obs
        years = sorted({e.year for e in entries})
        source_notes.append({
            "publisher": src["publisher"], "award": src["list_title"],
            "gender_served": src["gender_served"], "route": "wikipedia-api",
            "shape": "ordered_rank",
            "ranked_entries_parsed": len(entries),
            "runner_up_positions": stats["runner_up_positions"],
            "years": [years[0], years[-1]] if years else [],
            "observations_for_cohort": len(obs),
            "content_sha256": sha,
            "rows_skipped": stats["no_year"] + stats["no_winner"],
            # How often each parsing heuristic was load-bearing. A winner taken
            # from the fallback link is a structural guess that puts someone at
            # rank 1, and it used to be invisible.
            "winner_from_fallback": stats["winner_from_fallback"],
            "rank_beyond_declared_length": stats["rank_beyond_declared_length"],
        })
        print(f"{src['list_title']:30} entries={len(entries):3} "
              f"ranked={stats['runner_up_positions']} cohort hits={len(obs)}  "
              f"years={years[0]}-{years[-1]}"
              + (f"  fallback_winners={stats['winner_from_fallback']}"
                 if stats["winner_from_fallback"] else "")
              + (f"  beyond_length={stats['rank_beyond_declared_length']}"
                 if stats["rank_beyond_declared_length"] else ""))

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
            "partner_universe_matched": sorted(
                {n for n, q in name_to_person.items()
                 if q in people_with and q not in
                 {c["wikidata_qid"] for c in cohort["people"]}}
            ),
        },
    }
    (out / "observations.json").write_text(json.dumps(payload, indent=2))

    names = {p["wikidata_qid"]: p["display_name"] for p in cohort["people"]}
    print("\nobservations per cohort member:")
    for qid, n in per_person.most_common():
        print(f"  {names.get(qid, qid):22} {gender.get(qid,'?'):7} {n}")
    if payload["coverage"]["partner_universe_matched"]:
        print("\npartners matched from the list articles:")
        for n in payload["coverage"]["partner_universe_matched"]:
            print(f"  {n}")
    print("\ncohort members with no observations at all:")
    for n in payload["coverage"]["people_with_none"]:
        print(f"  {n}")
    print(f"\nby gender: {dict(by_gender)}")
    print(f"wrote {out / 'observations.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
