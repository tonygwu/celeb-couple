#!/usr/bin/env python3
"""Is a person absent from the corpus, or absent from the sources?

The report says four of fourteen cohort members carry no observation at all.
That sentence has two very different readings. "We looked and found nothing"
invites someone to look harder. "The permitted sources do not name this person
in any year" is a finding, and it is the one the project's negative conclusion
needs.

Nothing distinguished them. This does: every source table is re-fetched and
searched for the person's name across every year it covers, including the rows
the observation pipeline discards -- an unranked entry, a year outside the
cohort's adult window, a name that never reaches `name_to_person`.

A person found here but absent from the corpus is a pipeline gap and should be
investigated. A person absent from both is evidence about the REACHABLE
sources, which is a narrower claim and the one this file makes.

THE LIMIT, stated because the verdict is easy to over-read. Wikipedia does not
reproduce these lists in full: it carries the single winner for Maxim's Hot 100
and Esquire's Sexiest Woman Alive, and only the top ten of FHM's hundred. So a
person can be absent from every table here and still have appeared at number 37
in a published list. That is not a hole in this check -- it is the project's
actual constraint, the same one docs/SOURCE-HUNT.md concludes on -- but it
means the finding is "no permitted ROUTE reaches evidence about this person",
never "no publication ever rated them".

Hits the network. Spends no model quota.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require                          # noqa: E402
from packages.wiki.fetch import article_text                           # noqa: E402
from modules.consensus.wikipedia_lists import fetch_section_wikitext   # noqa: E402

#: Every permitted source the pipeline reads, as (page, section, label).
#: Kept in step with scripts/fetch_observations.py.
SOURCES = [
    ("People (magazine)", 4, "Sexiest Man Alive"),
    ("People (magazine)", 9, "Most Beautiful"),
    ("Maxim (magazine)", 6, "Maxim Hot 100"),
    ("Esquire (magazine)", 6, "Sexiest Woman Alive"),
    ("FHM's 100 Sexiest Women (UK)", 2, "FHM 100 Sexiest Women"),
]


def surname(name: str) -> str:
    return name.split()[-1]


def main() -> int:
    ap = argparse.ArgumentParser(
        description=("For cohort members with no observations, say whether the "
                     "permitted sources name them at all. Hits the network; "
                     "spends no quota."))
    ap.add_argument("--cohort", default="docs/pilot-cohort.json")
    ap.add_argument("--observations", default="data/pilot/observations/observations.json")
    ap.add_argument("--out", default="data/pilot/run/absence_audit.json")
    args = ap.parse_args()

    people = require(REPO, args.cohort)["people"]
    obs = require(REPO, args.observations)
    have = {o["person_id"] for o in obs["observations"]}
    missing = [p for p in people if p["wikidata_qid"] not in have]

    tables = {}
    for page, sec, label in SOURCES:
        tables[label] = fetch_section_wikitext(page, sec)[0]

    rows = []
    for p in missing:
        name = p["display_name"]
        named_in, surname_only = [], []
        for label, wt in tables.items():
            if name in wt:
                named_in.append(label)
            elif re.search(rf"\b{re.escape(surname(name))}\b", wt):
                # A surname alone is not this person. It is a prompt to look,
                # and it is reported separately for exactly that reason.
                surname_only.append(label)
        # The biographical article is the prose route the corpus also uses.
        try:
            bio = article_text(name)
        except Exception as exc:                                  # noqa: BLE001
            bio, bio_err = "", f"{type(exc).__name__}"
        else:
            bio_err = None
        # The FULL list name, never its first word. Matching `label.split()[0]`
        # was tried first and flagged Adam Sandler, because "Most" appears in
        # almost any long article. A substring that common is not evidence.
        prose_hits = sorted({label for _, _, label in SOURCES
                             if label in bio}) if bio else []
        rows.append({
            "person": name, "wikidata_qid": p["wikidata_qid"],
            "gender": p["gender_category"],
            "named_in_source_tables": named_in,
            "surname_only_in": surname_only,
            "publisher_named_in_own_article": prose_hits,
            "biography_error": bio_err,
            # Named for what it supports. "absent_from_every_permitted_source"
            # was the first wording and claims too much: Wikipedia carries only
            # the winner of Maxim and Esquire and only FHM's top ten, so this
            # is absence from the REACHABLE surface, not from the lists.
            "verdict": ("no_permitted_route_reaches_them" if not named_in
                        and not prose_hits else "named_somewhere_investigate"),
        })

    payload = {
        "cohort": args.cohort,
        "cohort_size": len(people),
        "with_observations": len(people) - len(missing),
        "checked": len(rows),
        "sources_searched": [label for _, _, label in SOURCES],
        "rows": rows,
        "note": ("Searches the WHOLE table, including rows the pipeline "
                 "discards, so a person found here but absent from the corpus "
                 "is a pipeline gap rather than a source gap. A surname-only "
                 "match is reported separately and is not a finding. "
                 "Wikipedia carries only the winner of Maxim and Esquire and "
                 "only FHM's top ten, so a verdict of "
                 "no_permitted_route_reaches_them means no reachable evidence "
                 "exists, NOT that no publication ever rated the person."),
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")

    for r in rows:
        print(f"  {r['verdict']:36} {r['person'][:20]:20} "
              f"tables={r['named_in_source_tables'] or '-'} "
              f"surname_only={r['surname_only_in'] or '-'} "
              f"own_article_mentions={r['publisher_named_in_own_article'] or '-'}")
    absent = sum(1 for r in rows if r["verdict"] == "no_permitted_route_reaches_them")
    print(f"\n{absent} of {len(rows)} carry no observation because no permitted "
          f"route reaches evidence about them, not because nobody looked.")
    print("  Wikipedia reproduces only the winner of Maxim and Esquire and only "
          "FHM's top ten, so this is absence from the REACHABLE surface rather "
          "than from the published lists.")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
