#!/usr/bin/env python3
"""Seed filmographies and their full billed cast, from the local IMDb dumps.

FREE. Reads only local files. Spends nothing.

Deliberately NOT in run_chain.sh, for the same reason as expand_roster.py: this
builds an INPUT to the pipeline, not a stage of it. Re-deriving it on every free
pass would move the cohort under the artifacts derived from it.

The dumps are NOT in the repo and never will be: they are about 2 GB and not
ours to redistribute. Point --dumps at a local directory, or set CELEB_IMDB_DIR.

WHY PERSON-FIRST. The obvious rule -- top-billed actor plus top-billed actress
of every romance-tagged film -- was measured and fails twice. It returns Bruce
Willis and Liv Tyler for Armageddon, who play father and daughter. And it drops
the female lead entirely in 6.8% of films against 0.6% for the male lead, which
is a bias in the metric rather than a coverage detail. Billing order is
unreliable for picking a couple and reliable for listing a person's films, so
this script does only the second thing. scripts/identify_couples.py picks the
couples.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

#: Every dump this script reads. Named so a missing one fails by name.
NEEDED = ("title.basics", "title.ratings", "title.principals", "name.basics")


def rows(dumps: Path, name: str):
    path = dumps / f"{name}.tsv.gz"
    with gzip.open(path, "rt", encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        for line in f:
            yield dict(zip(header, line.rstrip("\n").split("\t")))


def resolve_dumps(flag: str | None) -> Path:
    """Refuse rather than guess. A missing dump is not an empty corpus."""
    raw = flag or os.environ.get("CELEB_IMDB_DIR")
    if not raw:
        raise SystemExit(
            "no IMDb dump directory. Pass --dumps <dir> or set CELEB_IMDB_DIR.\n"
            "Download the bulk files from https://developer.imdb.com/"
            "non-commercial-datasets/ and keep them OUTSIDE the repo.")
    d = Path(raw).expanduser()
    missing = [n for n in NEEDED if not (d / f"{n}.tsv.gz").exists()]
    if missing:
        raise SystemExit(f"{d} is missing these dumps: {', '.join(missing)}")
    return d


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Build seed filmographies and their billed cast from the "
                    "local IMDb dumps. Free.")
    ap.add_argument("--dumps", default=None, help="directory holding the .tsv.gz files")
    ap.add_argument("--roster", default="docs/seed-roster.json")
    ap.add_argument("--min-votes", type=int, default=1000,
                    help="drop a seed film below this many IMDb votes. Reported, "
                         "not silent: the cut count is written into the artifact.")
    ap.add_argument("--out", default="data/imdb/seed_graph.json")
    args = ap.parse_args()

    dumps = resolve_dumps(args.dumps)
    roster = json.loads((REPO / args.roster).read_text())
    want = set(roster["men"]) | set(roster["women"])
    sex_of_name = {n: "male" for n in roster["men"]}
    sex_of_name.update({n: "female" for n in roster["women"]})

    # --- resolve names to nconst, disambiguating on billed movie credits ---
    cands = collections.defaultdict(list)
    for r in rows(dumps, "name.basics"):
        if r["primaryName"] in want:
            cands[r["primaryName"]].append(r["nconst"])
    unresolved = sorted(want - set(cands))
    if unresolved:
        raise SystemExit(f"these roster names match no IMDb person: {unresolved}")

    votes = {}
    for r in rows(dumps, "title.ratings"):
        try:
            votes[r["tconst"]] = int(r["numVotes"])
        except ValueError:
            pass

    films = {}
    for r in rows(dumps, "title.basics"):
        if r["titleType"] not in ("movie", "tvMovie") or r["isAdult"] != "0":
            continue
        if not r["startYear"].isdigit():
            continue
        films[r["tconst"]] = {"title": r["primaryTitle"], "year": int(r["startYear"]),
                              "genres": r["genres"], "votes": votes.get(r["tconst"], 0)}

    all_cand = {n for v in cands.values() for n in v}
    credits = collections.Counter()
    cast = collections.defaultdict(list)
    seen_by = collections.defaultdict(set)
    for r in rows(dumps, "title.principals"):
        if r["tconst"] not in films or r["category"] not in ("actor", "actress"):
            continue
        cast[r["tconst"]].append([int(r["ordering"]), r["nconst"],
                                  r["category"], r["characters"]])
        if r["nconst"] in all_cand:
            credits[r["nconst"]] += 1
            seen_by[r["nconst"]].add(r["tconst"])

    seed = {}
    for name in sorted(want):
        best = max(cands[name], key=lambda n: credits[n])
        if credits[best] == 0:
            raise SystemExit(f"{name}: best IMDb match {best} has no billed movie credit")
        seed[name] = best

    # --- the films, and what the vote floor cut ---
    seed_films = {t for n in seed.values() for t in seen_by[n]}
    keep = {t for t in seed_films if films[t]["votes"] >= args.min_votes}
    cut = sorted(seed_films - keep, key=lambda t: -films[t]["votes"])

    names_needed = {c[1] for t in keep for c in cast[t]}
    name_of = {}
    for r in rows(dumps, "name.basics"):
        if r["nconst"] in names_needed:
            name_of[r["nconst"]] = r["primaryName"]

    out = {
        "roster_version": roster["version"],
        "min_votes": args.min_votes,
        "counts": {
            "seed_people": len(seed),
            "seed_films_all": len(seed_films),
            "seed_films_kept": len(keep),
            "seed_films_cut_by_vote_floor": len(cut),
            "distinct_billed_people_in_kept_films": len(names_needed),
        },
        "seed": {name: {"nconst": n, "sex": sex_of_name[name]} for name, n in seed.items()},
        "films": {t: films[t] for t in sorted(keep)},
        "cast": {t: sorted(cast[t]) for t in sorted(keep)},
        "name_of": name_of,
        "cut_by_vote_floor": [{"tconst": t, **films[t]} for t in cut[:50]],
    }
    dest = REPO / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=1))
    c = out["counts"]
    print(f"seed people {c['seed_people']}   films {c['seed_films_all']:,} "
          f"-> kept {c['seed_films_kept']:,} (cut {c['seed_films_cut_by_vote_floor']:,} "
          f"below {args.min_votes:,} votes)")
    print(f"distinct billed people in kept films: "
          f"{c['distinct_billed_people_in_kept_films']:,}")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
