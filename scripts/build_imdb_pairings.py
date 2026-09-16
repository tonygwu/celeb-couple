#!/usr/bin/env python3
"""Turn identified couples into pairings the boards can read. FREE.

Joins three artifacts and nothing else:
  couples_cache.json  -- which two ACTORS are a couple in a film, and its weight
  person_bridge.json  -- nconst -> Wikidata QID, joined on P345
  seed_graph.json     -- the film's title and year

WHAT IS DROPPED, AND COUNTED. A pair is dropped when it is `incidental`, when
either person has no QID, or when Wikidata records no sex for one of them. Every
drop is counted by reason in the artifact, because a filter whose losses are
invisible is how a corpus quietly becomes a sample.

SEX COMES FROM WIKIDATA P21, never from IMDb's actor/actress category. The
category is about the billing credit; P21 is about the person. They usually
agree, and where they do not, the person is the thing being scored.

Every pairing here is `on_screen`. Real-life pairings come from the Wikidata
relationship route and are not touched by this script.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.artifacts import require        # noqa: E402

SEX = {"male": "male", "female": "female"}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Join couples + bridge + films into a pairings artifact. Free.")
    ap.add_argument("--couples", default="data/imdb/couples_cache.json")
    ap.add_argument("--bridge", default="data/imdb/person_bridge.json")
    ap.add_argument("--graph", default="data/imdb/seed_graph.json")
    ap.add_argument("--min-year", type=int, default=1990,
                    help="SCOPE, not a filter of convenience: the board covers films "
                         "from this year on, and the page says so. Applied here so the "
                         "scorer never pays for a person-year the board cannot show.")
    ap.add_argument("--out", default="data/imdb/imdb_pairings.json")
    args = ap.parse_args()

    couples = require(REPO, args.couples)
    bridge = require(REPO, args.bridge)["bridge"]
    graph = require(REPO, args.graph)
    films, name_of = graph["films"], graph["name_of"]

    qid_of, sex_of = {}, {}
    for nconst, rec in bridge.items():
        nm = name_of.get(nconst)
        if not nm:
            continue
        qid_of[nm] = rec["qid"]
        if rec.get("gender") in SEX:
            sex_of[nm] = SEX[rec["gender"]]

    pairings, dropped = [], collections.Counter()
    seen = set()
    for entry in couples.values():
        t = entry["tconst"]
        film = films.get(t)
        if film is None:
            dropped["film not in the seed graph"] += 1
            continue
        for p in entry["pairs"]:
            if p["weight"] == "incidental":
                dropped["incidental"] += 1
                continue
            if film["year"] < args.min_year:
                dropped[f"film before the {args.min_year} scope floor"] += 1
                continue
            a, b = p["a"], p["b"]
            if a not in qid_of or b not in qid_of:
                dropped["no Wikidata id for one side"] += 1
                continue
            if a not in sex_of or b not in sex_of:
                dropped["Wikidata records no sex for one side"] += 1
                continue
            if sex_of[a] == sex_of[b]:
                # The metric is defined as (female - male) read from the man's
                # side, so it has no reading for a same-sex pair. Counted, not
                # hidden: this is a real limit of the measure, not a data fault.
                dropped["same-sex pair: the metric has no reading"] += 1
                continue
            man, woman = (a, b) if sex_of[a] == "male" else (b, a)
            pid = f"pr_imdb_{t}_{qid_of[man]}_{qid_of[woman]}"
            if pid in seen:
                dropped["duplicate pairing"] += 1
                continue
            seen.add(pid)
            pairings.append({
                "pairing_id": pid, "domain": "on_screen",
                "period": str(film["year"]), "work": film["title"],
                "male": man, "female": woman,
                "male_qid": qid_of[man], "female_qid": qid_of[woman],
                "gap": None, "judges": {}, "unjudged": {}, "reasonings": {},
                # Binarized upstream: a couple counts fully. Weight has already
                # decided membership, so it is carried for display, not scaling.
                "centrality": 1.0, "weight": p["weight"],
                "confidence": p["confidence"], "tconst": t,
                "characters": p.get("characters", ""),
            })

    people = {q for p in pairings for q in (p["male_qid"], p["female_qid"])}
    tuples = {(p["male_qid"], p["period"]) for p in pairings} | \
             {(p["female_qid"], p["period"]) for p in pairings}
    out = {
        "min_year": args.min_year,
        "counts": {
            "films_graded": len(couples), "pairings": len(pairings),
            "distinct_people": len(people), "person_years_needed": len(tuples),
            "dropped": dict(dropped.most_common()),
        },
        "pairings": sorted(pairings, key=lambda p: p["pairing_id"]),
    }
    dest = REPO / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    c = out["counts"]
    print(f"films graded {c['films_graded']:,} -> pairings {c['pairings']:,}")
    print(f"  distinct people {c['distinct_people']:,}   "
          f"person-years needed {c['person_years_needed']:,}")
    for reason, n in c["dropped"].items():
        print(f"  dropped, {reason}: {n:,}")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
