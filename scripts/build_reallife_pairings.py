#!/usr/bin/env python3
"""Real-life pairings from EVERY episode, not just one slice. FREE.

The real-life boards showed 4 people. The cause was not missing data: the only
real-life pairings the board could see came from `select_m1_slice.py`, which
narrows to 10 focal actors on purpose, because it exists to pick a pilot. The
episodes file already holds 228 usable relationships across 291 people, 70 of
whom have two or more.

One episode becomes one pairing, dated at its FIRST adult year, which is the
convention select_m1_slice.py already used. A relationship that ran 1989-1993
is dated 1989.

Sex comes from Wikidata P21, fetched once. A pairing whose two people share a
sex has no reading under a metric defined as (female - male), so it is counted
and dropped rather than guessed at.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.artifacts import require              # noqa: E402
from packages.llmkit.atomic import write_json_atomic       # noqa: E402
from modules.records.wikidata import fetch_gender          # noqa: E402

SEX = {"male": "male", "female": "female"}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Turn every scorable episode into a real-life pairing. Free.")
    ap.add_argument("--episodes", default="data/roster100/records/episodes.json")
    ap.add_argument("--min-year", type=int, default=1980)
    ap.add_argument("--gender-cache", default="data/roster100/records/gender.json")
    ap.add_argument("--out", default="data/roster100/run/reallife_pairings.json")
    args = ap.parse_args()

    eps = require(REPO, args.episodes)["episodes"]
    usable = [e for e in eps if e.get("scorable") and e.get("adult_years")]
    print(f"episodes {len(eps):,} -> scorable with adult years {len(usable):,}")

    qids = sorted({q for e in usable for q in (e["subject_qid"], e["partner_qid"])})
    cache_path = REPO / args.gender_cache
    gender = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    missing = [q for q in qids if q not in gender]
    if missing:
        print(f"  fetching sex for {len(missing):,} people from Wikidata P21")
        for chunk in (missing[i:i + 200] for i in range(0, len(missing), 200)):
            gender.update(fetch_gender(chunk))
        for q in missing:
            gender.setdefault(q, "")
        write_json_atomic(cache_path, gender, indent=1)

    out, dropped = [], collections.Counter()
    seen = set()
    for e in usable:
        year = min(e["adult_years"])
        if year < args.min_year:
            dropped[f"before the {args.min_year} scope floor"] += 1
            continue
        a, b = e["subject_qid"], e["partner_qid"]
        sa, sb = SEX.get(gender.get(a, "")), SEX.get(gender.get(b, ""))
        if not sa or not sb:
            dropped["Wikidata records no sex for one side"] += 1
            continue
        if sa == sb:
            dropped["same-sex pair: the metric has no reading"] += 1
            continue
        names = {a: e.get("subject_name") or a, b: e.get("partner_label") or b}
        man, woman = (a, b) if sa == "male" else (b, a)
        pid = f"pr_real_{man}_{woman}_{year}"
        if pid in seen:
            dropped["duplicate"] += 1
            continue
        seen.add(pid)
        out.append({"pairing_id": pid, "domain": "real_life", "period": str(year),
                    "work": None, "male": names[man], "female": names[woman],
                    "male_qid": man, "female_qid": woman,
                    "gap": None, "judges": {}, "unjudged": {}, "reasonings": {},
                    "centrality": 1.0, "episode_id": e["episode_id"],
                    "stages": e.get("stages", [])})

    people = collections.Counter()
    for p in out:
        people[p["male"]] += 1; people[p["female"]] += 1
    tuples = {(p["male_qid"], p["period"]) for p in out} | \
             {(p["female_qid"], p["period"]) for p in out}
    blob = {"min_year": args.min_year,
            "counts": {"pairings": len(out), "distinct_people": len(people),
                       "people_with_2_plus": sum(1 for v in people.values() if v >= 2),
                       "people_with_3_plus": sum(1 for v in people.values() if v >= 3),
                       "person_years_needed": len(tuples),
                       "dropped": dict(dropped.most_common())},
            "pairings": sorted(out, key=lambda p: p["pairing_id"])}
    write_json_atomic(REPO / args.out, blob, indent=1)
    c = blob["counts"]
    print(f"pairings {c['pairings']:,}  people {c['distinct_people']:,}  "
          f"2+ {c['people_with_2_plus']}  3+ {c['people_with_3_plus']}")
    print(f"  person-years needed: {c['person_years_needed']:,}")
    for k, v in c["dropped"].items():
        print(f"  dropped, {k}: {v}")
    print(f"wrote {REPO / args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
