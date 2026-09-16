#!/usr/bin/env python3
"""Bridge IMDb person ids to Wikidata ids. FREE, but it does fetch.

The two halves of this project key people differently. The score cache and the
published observations key on a Wikidata QID like `Q13909`. The IMDb graph keys
on an nconst like `nm0000138`. Nothing joins them, so a person discovered
through IMDb cannot be scored against the evidence the project already holds.

Wikidata property P345 IS the IMDb id, so the join is one query. This resolves
it in the ONLY safe direction: from nconst to QID. Matching on names instead
would silently merge two people who share one, and this corpus already contains
several such collisions.

Uses `batched_query`, which refuses a chunk that comes back at its row cap and
halves a chunk that times out. AGENTS.md records what a bare LIMIT cost here:
one query capped at 400 against 2,570 rows published 136 pairs instead of 808.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.artifacts import require                    # noqa: E402
from modules.records.wikidata import batched_query               # noqa: E402

#: Far above any honest answer: one nconst resolves to one person, so a chunk
#: of 200 cannot legitimately return more than a few hundred rows even with
#: duplicate statements. A chunk AT this number means truncation, and
#: batched_query raises on it.
ROW_LIMIT = 5000


def build(chunk: list[str]) -> str:
    values = " ".join(f'"{n}"' for n in chunk)
    return f"""
SELECT DISTINCT ?person ?imdb ?personLabel ?genderLabel WHERE {{
  VALUES ?imdb {{ {values} }}
  ?person wdt:P345 ?imdb .
  ?person wdt:P31 wd:Q5 .
  OPTIONAL {{ ?person wdt:P21 ?gender . }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}} LIMIT {ROW_LIMIT}
"""


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Resolve IMDb nconsts to Wikidata QIDs via P345. Free.")
    ap.add_argument("--graph", default="data/imdb/seed_graph.json")
    ap.add_argument("--couples", default="data/imdb/couples_cache.json")
    ap.add_argument("--chunk", type=int, default=200)
    ap.add_argument("--out", default="data/imdb/person_bridge.json")
    args = ap.parse_args()

    graph = require(REPO, args.graph)
    name_of = graph["name_of"]
    nconst_of_name: dict[str, str] = {}
    for n, nm in name_of.items():
        nconst_of_name.setdefault(nm, n)

    # Only people who actually appear in a board row are worth resolving.
    couples = require(REPO, args.couples)
    wanted_names, unresolvable = set(), set()
    for entry in couples.values():
        for p in entry["pairs"]:
            if p["weight"] == "incidental":
                continue
            for who in (p["a"], p["b"]):
                if who in nconst_of_name:
                    wanted_names.add(who)
                else:
                    # named by the judge but absent from IMDb's billed cast --
                    # Minnie Driver in Good Will Hunting is the type case
                    unresolvable.add(who)

    nconsts = sorted({nconst_of_name[n] for n in wanted_names})
    print(f"people in board rows: {len(wanted_names) + len(unresolvable)}")
    print(f"  with an IMDb id from the billed cast: {len(nconsts)}")
    print(f"  named by the judge but NOT in IMDb's cast: {len(unresolvable)}"
          f"   <- these need a name-based lookup, kept separate on purpose")

    rows = batched_query(build, nconsts, chunk_size=args.chunk,
                         limit=ROW_LIMIT, label="p345")

    bridge, collisions = {}, {}
    for r in rows:
        imdb = r["imdb"]["value"]
        qid = r["person"]["value"].rsplit("/", 1)[-1]
        rec = {"qid": qid, "name": r.get("personLabel", {}).get("value"),
               "gender": r.get("genderLabel", {}).get("value")}
        if imdb in bridge and bridge[imdb]["qid"] != qid:
            collisions.setdefault(imdb, [bridge[imdb]]).append(rec)
            continue
        bridge[imdb] = rec

    missing = [n for n in nconsts if n not in bridge]
    print(f"resolved: {len(bridge):,} of {len(nconsts):,}")
    print(f"  no Wikidata person carries that IMDb id: {len(missing):,}")
    print(f"  one IMDb id claimed by MORE THAN ONE Wikidata item: {len(collisions)}"
          f"   <- refused, not guessed")

    dest = REPO / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({
        "counts": {"wanted": len(nconsts), "resolved": len(bridge),
                   "unresolved": len(missing), "collisions": len(collisions),
                   "not_in_imdb_cast": len(unresolvable)},
        "bridge": bridge,
        "unresolved_nconsts": missing[:200],
        "collisions": collisions,
        "named_but_not_in_imdb_cast": sorted(unresolvable),
    }, indent=1))
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
