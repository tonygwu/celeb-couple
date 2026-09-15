#!/usr/bin/env python3
"""Grow a roster by snowballing over co-stars and real-life partners.

The roster is a CLOSED set, and that closure is invisible in the product. A
reader clicking Adam Sandler and asking why 50 First Dates is missing is not
looking at a data gap in Wikidata; Drew Barrymore is simply not one of the 100
names, so no query could ever have reached her. Same for Minnie Driver and
Good Will Hunting.

This script takes the current roster as SEEDS and repeats two hops:

  onscreen_costar      both credited as cast (P161) on the same film
  real_life_partner    spouse (P26) or unmarried partner (P451)

Round 1 expands the seeds. Every later round expands only what the previous
round ADDED, which is what keeps the cost roughly linear in new people rather
than quadratic in the roster.

WHAT THIS DOES NOT DO. It does not decide that a co-starring pair played a
romance; `scripts/classify_romance.py` does that and it spends model quota.
Everything here is a CANDIDATE, exactly like `fetch_onscreen_candidates.py`
output, and the same caveat applies.

SOURCES. Wikidata only (CC0), which is what every other fetcher in this
repository uses.

IMDb is NOT a source here. The request that prompted this script said "IMDB and
Wikipedia", and the standing instruction that came with it excludes IMDb
because its terms forbid repurposing its data to build a database of movie
information. That instruction is worth reading carefully, because the
repository does not actually record it: grep finds no IMDb policy in AGENTS.md,
in `docs/`, or anywhere in the git history, and there is no `docs/PLAN-v3.md`
in this checkout at all. What the repository DOES record is the
restricted-publisher list -- `docs/SOURCE-HUNT.md` marks people.com and
askmen.com "terms forbid LLM extraction and dataset creation" and maxim.com and
glamourmagazine.co.uk "AI crawlers disallowed", and `docs/PLAN-v4.md` keeps
that in force as a fetching rule. None of those is fetched here either.

BOUNDING. An unbounded snowball explodes. Two seeds alone -- Adam Sandler and
Matt Damon -- reach 2410 distinct co-stars with any Wikidata sitelink count at
all. Four separate bounds apply, all of them arguments with recorded defaults,
and every one of them reports what it cut:

  --min-sitelinks       prominence floor for a co-star edge
  --partner-min-sitelinks  the same floor for a partner edge, lower because a
                        named real-life partner is the operator's own ask
  --per-round-cap       how many people one round may admit
  --max-people          the roster may never exceed this
  --rounds              hard round ceiling
  --converge-at         stop early once a round admits fewer than this

Read-only. Spends no model quota.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require                       # noqa: E402
from modules.records import wikidata as wd                          # noqa: E402
from modules.records import wikidata as wdmod                       # noqa: E402
from modules.records.wikidata import (                              # noqa: E402
    TruncatedResult, _val, batched_query, fetch_gender, fetch_labels)

#: Wikidata sex-or-gender items this project's pairing product can use. A
#: person Wikidata records as anything else is LEFT OUT rather than guessed
#: into one of these, which is the same rule `fetch_gender` already follows.
GENDER_ITEMS = {"Q6581097": "male", "Q6581072": "female"}

#: Co-stars of the seeds, with the prominence signal in the same query so the
#: floor prunes server-side. `wikibase:sitelinks` is the number of Wikipedias
#: and sister projects holding an article about the person. It is CC0, stable
#: between runs, and needs no judgment call.
COSTAR_QUERY = """
SELECT DISTINCT ?seed ?other ?otherLabel ?g ?sl WHERE {
  VALUES ?seed { %s }
  ?film wdt:P31/wdt:P279* wd:Q11424 .
  ?film wdt:P161 ?seed , ?other .
  FILTER(?other != ?seed)
  ?other wdt:P31 wd:Q5 ; wdt:P21 ?g ; wikibase:sitelinks ?sl .
  FILTER(?sl >= %d)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
} LIMIT %d
"""

#: Spouses and unmarried partners. Same shape so the two edge types can be
#: ranked against each other.
PARTNER_QUERY = """
SELECT DISTINCT ?seed ?other ?otherLabel ?g ?sl WHERE {
  VALUES ?seed { %s }
  { ?seed wdt:P26 ?other } UNION { ?seed wdt:P451 ?other }
  ?other wdt:P31 wd:Q5 ; wdt:P21 ?g ; wikibase:sitelinks ?sl .
  FILTER(?sl >= %d)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
} LIMIT %d
"""


#: Seeds the query service could not answer for even one at a time. Reported in
#: the artifact rather than dropped, because a seed nobody could expand is a
#: hole in the snowball and the roster has to say so. This repository already
#: has `absence_audit.py` for exactly that distinction.
UNREACHABLE_SEEDS: list[dict] = []


def _fetch(query: str, seeds: list[str], floor: int, limit: int,
           chunk_size: int, label: str) -> list[dict]:
    """Batch the seeds through `batched_query`, which owns both guards.

    A batch at its LIMIT raises. A batch that TIMES OUT is halved and retried
    down to one seed, and a single seed that still times out is recorded here
    rather than skipped.
    """
    return batched_query(
        lambda chunk: query % (" ".join(f"wd:{q}" for q in chunk), floor, limit),
        seeds, chunk_size, limit, label=label,
        on_unreachable=lambda seed, exc: UNREACHABLE_SEEDS.append(
            {"seed": seed, "edge": label, "error": str(exc)}))


def collect(rows: list[dict], edge: str, known: set[str]) -> dict[str, dict]:
    """Fold SPARQL rows into one record per NEW person.

    `seeds` is the set of THIS ROUND'S seeds that reach the candidate, and its
    size is the ranking signal that matters: somebody who co-starred with six
    of them sits closer to the roster's centre than somebody who appeared
    beside one of them once.

    Note what that is NOT. From round 2 on the seeds are the previous round's
    admissions, not the whole roster, so reach is measured against the frontier
    rather than against everybody. That is the BFS choice which keeps the cost
    linear in new people; the price is that a round-2 candidate who also
    co-starred with forty original roster members is ranked only on their
    round-1 reach.
    """
    out: dict[str, dict] = {}
    for r in rows:
        qid = (_val(r, "other") or "").rsplit("/", 1)[-1]
        seed = (_val(r, "seed") or "").rsplit("/", 1)[-1]
        gq = (_val(r, "g") or "").rsplit("/", 1)[-1]
        if not qid or qid in known or gq not in GENDER_ITEMS:
            continue
        rec = out.setdefault(qid, {
            "wikidata_qid": qid,
            "display_name": _val(r, "otherLabel") or qid,
            "gender_category": GENDER_ITEMS[gq],
            "sitelinks": int(_val(r, "sl") or 0),
            "edges": set(),
            "seeds": set(),
        })
        rec["edges"].add(edge)
        rec["seeds"].add(seed)
    return out


def merge(a: dict[str, dict], b: dict[str, dict]) -> dict[str, dict]:
    """Union two candidate maps, keeping both edge types on a person in both."""
    for qid, rec in b.items():
        if qid in a:
            a[qid]["edges"] |= rec["edges"]
            a[qid]["seeds"] |= rec["seeds"]
        else:
            a[qid] = rec
    return a


def rank_key(rec: dict) -> tuple:
    """Sort order for admission, highest first.

    A real-life partner outranks a pure co-star. That is deliberate and it is
    the operator's own framing: "romantically co-starred with AND also dated in
    real life". Wikidata can source the dating half and cannot source the
    romance half without a model call, so the half it can source gets the
    weight.

    After that, reach into the current roster, then prominence, then the Q-id
    so the order never depends on dict iteration.
    """
    return (
        1 if "real_life_partner" in rec["edges"] else 0,
        len(rec["seeds"]),
        rec["sitelinks"],
        -int(rec["wikidata_qid"][1:]),
    )


def admit(cands: dict[str, dict], cap: int, balance: bool,
          headroom: int) -> tuple[list[dict], int]:
    """Choose which candidates a round takes, and say how many it turned away.

    With `balance` on, the cap is split evenly between the two sexes. The seed
    roster is deliberately 50 male and 50 female -- `docs/roster-100.json` says
    "both genders equally" -- and an unbalanced snowball would quietly undo
    that, because a male-led film's cast is not evenly split.
    """
    cap = min(cap, headroom)
    ordered = sorted(cands.values(), key=rank_key, reverse=True)
    if not balance:
        taken = ordered[:cap]
    else:
        half = cap // 2
        by_sex = {"male": [], "female": []}
        for rec in ordered:
            by_sex[rec["gender_category"]].append(rec)
        taken = by_sex["male"][:half] + by_sex["female"][:cap - half]
        # A sex with fewer candidates than its half leaves room the other can
        # use. Refusing to fill it would cut people for no reason.
        short = cap - len(taken)
        if short > 0:
            chosen = {r["wikidata_qid"] for r in taken}
            rest = [r for r in ordered if r["wikidata_qid"] not in chosen]
            taken += rest[:short]
        taken.sort(key=rank_key, reverse=True)
    return taken, len(ordered) - len(taken)


def build_parser() -> argparse.ArgumentParser:
    """Separate from main() so a test can read every bound's default without
    running a snowball. The bounds ARE the contract of this script."""
    ap = argparse.ArgumentParser()
    ap.add_argument("--roster", default="docs/roster-100.json")
    ap.add_argument("--out", default="docs/roster-expanded.json")
    ap.add_argument("--rounds", type=int, default=3,
                    help="hard ceiling on snowball rounds (default 3)")
    ap.add_argument("--converge-at", type=int, default=10,
                    help="stop once a round admits fewer than this (default 10)")
    ap.add_argument("--per-round-cap", type=int, default=60,
                    help="people one round may admit (default 60)")
    ap.add_argument("--max-people", type=int, default=400,
                    help="the roster may never exceed this (default 400)")
    ap.add_argument("--min-sitelinks", type=int, default=40,
                    help="prominence floor for a co-star edge (default 40)")
    ap.add_argument("--partner-min-sitelinks", type=int, default=20,
                    help="prominence floor for a partner edge (default 20)")
    ap.add_argument("--balance", dest="balance", action="store_true", default=True,
                    help="split each round's cap evenly between the sexes (default)")
    ap.add_argument("--no-balance", dest="balance", action="store_false")
    ap.add_argument("--must-include", default="",
                    help="comma-separated Wikidata Q-ids to put on the roster "
                         "as seeds regardless of rank. A bounded snowball "
                         "cannot promise a specific person; this is how you "
                         "ask for one.")
    ap.add_argument("--edges", default="partner,costar",
                    help="which hops to take (default partner,costar)")
    ap.add_argument("--chunk-size", type=int, default=5,
                    help="seeds per SPARQL batch (default 5)")
    ap.add_argument("--row-limit", type=int, default=20000,
                    help="row cap per batch; a batch that reaches it is refused")
    return ap


def seed_named(qids: list[str], known: set[str]) -> tuple[list[dict], list[str]]:
    """Put explicitly named people on the roster as seeds, ahead of any round.

    A bounded snowball cannot promise a SPECIFIC person, and pretending it can
    would be the dishonest answer. Minnie Driver is the worked example: she is
    rank 455 among round-1 women, so a balanced per-round cap would have to be
    at least 910 to reach her, which is a roster of 1010 after one round. The
    operator's complaint is that clicking any one actor must not show an
    unexplained gap, and the fix for a named gap is to name the person.

    They enter as SEEDS rather than as admissions, so they never displace a
    ranked candidate and the per-round cap keeps meaning what it says. Their
    row records `named_explicitly`, so nobody later reads them as something
    the snowball found.

    Gender and name come from Wikidata, never from the caller. Somebody whose
    sex-or-gender Wikidata does not record as male or female is refused, with
    a reason, because the pairing product needs one of each.
    """
    wanted = [q for q in qids if q not in known]
    if not wanted:
        return [], []
    genders = fetch_gender(wanted)
    labels = fetch_labels(wanted)
    people, refused = [], []
    for qid in wanted:
        gender = (genders.get(qid) or "").lower()
        name = labels.get(qid)
        if gender not in ("male", "female"):
            refused.append(f"{qid}: sex-or-gender is {gender or 'unrecorded'}")
            continue
        if not name:
            refused.append(f"{qid}: no English label and no English Wikipedia article")
            continue
        people.append({
            "display_name": name,
            "wikidata_qid": qid,
            "gender_category": gender,
            "cohort_note": "named explicitly (--must-include)",
            "named_explicitly": True,
        })
    return people, refused


def resolve_bare_qids(roster: list[dict]) -> tuple[list[str], list[str]]:
    """Give a name to anybody the label SERVICE returned as a bare Q-id.

    Eleven of the original hundred roster members have NO English label in
    Wikidata at all, despite labels in dozens of other languages, and the label
    SERVICE hands those back as the Q-id. A roster row reading "Q2023710" names
    nobody, and this repository has already paid for it once: two pilot
    partners and ten roster partners entered the corpus as bare ids and their
    episodes were excluded as defective.

    The English Wikipedia SITELINK is the fallback, because an article title is
    a sourced name rather than a guess. Somebody with neither stays a bare id
    and is REPORTED, not hidden.

    Returns (resolved qids, still-unresolved qids).
    """
    bare = [p["wikidata_qid"] for p in roster
            if re.fullmatch(r"Q\d+", str(p["display_name"]))]
    if not bare:
        return [], []
    labels = fetch_labels(sorted(set(bare)))
    for person in roster:
        got = labels.get(person["wikidata_qid"])
        if got and re.fullmatch(r"Q\d+", str(person["display_name"])):
            person["display_name"] = got
            person["name_source"] = wdmod.LABEL_SOURCES.get(
                person["wikidata_qid"], "label")
    still = sorted({q for q in bare if q not in labels})
    return sorted(set(bare) - set(still)), still


def main() -> int:
    args = build_parser().parse_args()

    edges = {e.strip() for e in args.edges.split(",") if e.strip()}
    unknown = edges - {"partner", "costar"}
    if unknown:
        print(f"unknown edge type(s): {sorted(unknown)}")
        return 1

    seed_doc = require(REPO, args.roster)
    roster = [dict(p) for p in seed_doc["people"]]
    known = {p["wikidata_qid"] for p in roster}

    named = [q.strip() for q in args.must_include.split(",") if q.strip()]
    bad = [q for q in named if not re.fullmatch(r"Q\d+", q)]
    if bad:
        print(f"--must-include takes Wikidata Q-ids; these are not: {bad}")
        return 1
    added, refused_named = seed_named(named, known)
    for person in added:
        roster.append(person)
        known.add(person["wikidata_qid"])
    if added:
        print("named explicitly: "
              + ", ".join(f"{p['display_name']} ({p['wikidata_qid']})" for p in added))
    if refused_named:
        print("REFUSED from --must-include: " + "; ".join(refused_named))

    seed_qids = sorted(known)
    frontier = seed_qids
    rounds_log: list[dict] = []
    stopped = "rounds_exhausted"

    for rnd in range(1, args.rounds + 1):
        headroom = args.max_people - len(roster)
        if headroom <= 0:
            stopped = "max_people_reached"
            break
        expanded = len(frontier)
        print(f"round {rnd}: expanding {expanded} seed(s), "
              f"roster {len(roster)}, headroom {headroom}")
        t0 = time.time()
        cands: dict[str, dict] = {}
        raw_rows = 0
        if "partner" in edges:
            rows = _fetch(PARTNER_QUERY, frontier, args.partner_min_sitelinks,
                          args.row_limit, args.chunk_size, "partner")
            raw_rows += len(rows)
            cands = merge(cands, collect(rows, "real_life_partner", known))
        if "costar" in edges:
            rows = _fetch(COSTAR_QUERY, frontier, args.min_sitelinks,
                          args.row_limit, args.chunk_size, "costar")
            raw_rows += len(rows)
            cands = merge(cands, collect(rows, "onscreen_costar", known))

        taken, cut = admit(cands, args.per_round_cap, args.balance, headroom)
        for rec in taken:
            roster.append({
                "display_name": rec["display_name"],
                "wikidata_qid": rec["wikidata_qid"],
                "gender_category": rec["gender_category"],
                "cohort_note": f"snowball round {rnd}",
                "expansion": {
                    "round": rnd,
                    "edges": sorted(rec["edges"]),
                    "reached_from": sorted(rec["seeds"]),
                    "sitelinks": rec["sitelinks"],
                },
            })
        known |= {r["wikidata_qid"] for r in taken}
        frontier = [r["wikidata_qid"] for r in taken]

        log = {
            "round": rnd,
            "seeds_expanded": expanded,
            "sparql_rows": raw_rows,
            "candidates_after_floor": len(cands),
            "admitted": len(taken),
            "cut_by_cap": cut,
            "admitted_male": sum(1 for r in taken if r["gender_category"] == "male"),
            "admitted_female": sum(1 for r in taken if r["gender_category"] == "female"),
            "roster_size_after": len(roster),
            "seconds": round(time.time() - t0, 1),
        }
        rounds_log.append(log)
        print(f"  round {rnd}: {len(cands)} candidate(s) over the floor, "
              f"{len(taken)} admitted ({log['admitted_male']}M/"
              f"{log['admitted_female']}F), {cut} cut by the cap, "
              f"roster now {len(roster)}")

        if len(taken) < args.converge_at:
            stopped = "converged"
            break
        if not frontier:
            stopped = "no_frontier"
            break
        if len(roster) >= args.max_people:
            stopped = "max_people_reached"
            break

    resolved, unresolved = resolve_bare_qids(roster)
    if resolved:
        print(f"named {len(resolved)} person/people the label service returned "
              "as bare Q-ids, via their English Wikipedia sitelink")
    if unresolved:
        print(f"WARNING: {len(unresolved)} person/people have no English label "
              f"and no English Wikipedia article: {', '.join(unresolved)}")

    payload = {
        "version": f"roster-expanded-{datetime.now(timezone.utc):%Y-%m-%d}",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "wikidata P161 co-appearance + P26/P451 partners",
        "seed_roster": args.roster,
        "seed_size": len(seed_doc["people"]),
        # Named people are SEEDS, not admissions, so they never displace a
        # ranked candidate. Recorded so nobody reads them as something the
        # snowball found on its own.
        "named_explicitly": [p["wikidata_qid"] for p in added],
        "named_explicitly_refused": refused_named,
        "status": "UNVERIFIED CANDIDATES",
        "caveat": (
            "A co-star edge proves only that both were credited on the same "
            "film. It does NOT say their characters were a couple; "
            "scripts/classify_romance.py decides that and it spends model "
            "quota. IMDb is not a source here: plan v3 section 3 excludes it."),
        "stopping_rule": {
            "stopped_because": stopped,
            "rounds_ceiling": args.rounds,
            "converge_at": args.converge_at,
            "per_round_cap": args.per_round_cap,
            "max_people": args.max_people,
            "min_sitelinks": args.min_sitelinks,
            "partner_min_sitelinks": args.partner_min_sitelinks,
            "balance_sexes": args.balance,
            "edges": sorted(edges),
            "must_include": named,
        },
        "rounds": rounds_log,
        # A seed the service could not answer for is a hole in the snowball.
        # Named, with a count, because "nobody looked" and "nothing is there"
        # are the distinction this repository already built absence_audit.py
        # to keep apart.
        "unreachable_seeds": list(UNREACHABLE_SEEDS),
        # A roster row reading "Q2023710" names nobody. Which route supplied a
        # name is recorded per person in `name_source`; these are the counts.
        "names_from_enwiki_sitelink": resolved,
        "names_unresolved": unresolved,
        "people": roster,
    }
    dest = REPO / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2))
    if UNREACHABLE_SEEDS:
        print(f"\nWARNING: {len(UNREACHABLE_SEEDS)} seed(s) the query service "
              f"could not answer for, recorded in the artifact: "
              + ", ".join(sorted({u["seed"] for u in UNREACHABLE_SEEDS})))
    print(f"\nroster {len(seed_doc['people'])} -> {len(roster)} "
          f"({sum(1 for p in roster if p['gender_category'] == 'male')}M/"
          f"{sum(1 for p in roster if p['gender_category'] == 'female')}F), "
          f"stopped because: {stopped}")
    for r in rounds_log:
        print(f"  round {r['round']}: +{r['admitted']} "
              f"({r['cut_by_cap']} cut by the cap)")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
