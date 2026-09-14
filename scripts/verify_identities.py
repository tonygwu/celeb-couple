#!/usr/bin/env python3
"""Check that every roster Wikidata id is the person the roster says it is.

A wrong Q-id is the quietest possible error in this project. Everything about
that person -- their relationships, their observations, their estimates --
would be fetched correctly and be about somebody else, and nothing downstream
could tell. Nothing checked it.

The check is deliberately not "does the label match". Eleven of the hundred
roster members have NO English label in Wikidata at all, despite labels in
dozens of other languages, so a label comparison would report elevens errors
that are not errors. The English Wikipedia SITELINK is the fallback, because a
sitelink is a sourced name rather than a guess.

A trailing disambiguator is tolerated: the enwiki title for Q178348 is "Chris
Evans (actor)" and the person is Chris Evans. It is tolerated, not stripped
silently -- the report says which rows needed it.

Hits the network. Spends no model quota.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402
from packages.wiki.fetch import USER_AGENT  # noqa: E402

API = "https://www.wikidata.org/w/api.php"
#: Wikidata's "human". A roster entry that is not one is a category, a film or
#: a disambiguation page, and every fact fetched under it is nonsense.
HUMAN = "Q5"
#: wbgetentities takes at most 50 ids per request.
BATCH = 50
_DISAMBIGUATOR = re.compile(r"\s*\([^)]*\)$")


def strip_disambiguator(title: str) -> str:
    """"Chris Evans (actor)" -> "Chris Evans"."""
    return _DISAMBIGUATOR.sub("", title).strip()


def resolve(entity: dict) -> tuple[str | None, str]:
    """Return (name, how it was found).

    The English label first, the English Wikipedia sitelink second. An entity
    with neither returns None rather than a Q-id dressed up as a name; two
    partners once entered this corpus as bare ids and the report printed them.
    """
    label = (entity.get("labels", {}).get("en") or {}).get("value")
    if label:
        return label, "label"
    title = (entity.get("sitelinks", {}).get("enwiki") or {}).get("title")
    if title:
        return title, "enwiki sitelink"
    return None, "nothing"


def is_human(entity: dict) -> bool:
    return any(
        s["mainsnak"].get("datavalue", {}).get("value", {}).get("id") == HUMAN
        for s in entity.get("claims", {}).get("P31", [])
    )


def fetch(qids: list[str], timeout: int = 60) -> dict:
    out: dict = {}
    for i in range(0, len(qids), BATCH):
        url = API + "?" + urllib.parse.urlencode({
            "action": "wbgetentities", "ids": "|".join(qids[i:i + BATCH]),
            "props": "labels|sitelinks|claims", "languages": "en",
            "sitefilter": "enwiki", "format": "json"})
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as fh:
            out.update(json.load(fh)["entities"])
    return out


def check(people: list[dict], entities: dict) -> list[dict]:
    rows = []
    for p in people:
        qid, want = p["wikidata_qid"], p["display_name"]
        e = entities.get(qid) or {}
        name, how = resolve(e)
        if "missing" in e:
            verdict = "no_such_entity"
        elif not is_human(e):
            verdict = "not_a_human"
        elif name is None:
            verdict = "no_english_name"
        elif name == want:
            verdict = "exact"
        elif strip_disambiguator(name) == want:
            verdict = "exact_after_disambiguator"
        else:
            verdict = "name_mismatch"
        rows.append({"wikidata_qid": qid, "display_name": want,
                     "wikidata_name": name, "resolved_by": how,
                     "verdict": verdict})
    return rows


#: Verdicts that mean the roster is wrong about who this is.
FAILING = {"no_such_entity", "not_a_human", "no_english_name", "name_mismatch"}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=("Check every roster Wikidata id is the person named. "
                     "Hits the network; spends no quota."))
    ap.add_argument("--roster", default="docs/pilot-cohort.json")
    ap.add_argument("--out", default="data/pilot/run/identity_verification.json")
    args = ap.parse_args()

    people = require(REPO, args.roster)["people"]
    rows = check(people, fetch([p["wikidata_qid"] for p in people]))

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    failures = [r for r in rows if r["verdict"] in FAILING]

    # The interesting number, and it is invisible in the verdicts because a
    # sitelink fallback that works produces an "exact" row. Wikidata has no
    # English label for eleven of the hundred roster members, so any code that
    # reads a label and does not fall back is wrong about 11% of the roster.
    fallback = [r for r in rows if r["resolved_by"] == "enwiki sitelink"]
    payload = {
        "roster": args.roster, "checked": len(rows),
        "verdict_counts": counts, "failures": failures,
        "resolved_by_sitelink_because_no_english_label":
            [r["display_name"] for r in fallback],
        "rows": rows,
        "note": ("A label comparison alone would report an error for every "
                 "person Wikidata has no English label for, and there are "
                 "eleven of those in the 100-name roster. The English "
                 "Wikipedia sitelink is the fallback because it is a sourced "
                 "name rather than a guess."),
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")

    for r in rows:
        if r["verdict"] != "exact":
            print(f"  {r['verdict']:26} {r['wikidata_qid']:10} "
                  f"{r['display_name'][:24]:24} -> {r['wikidata_name']} "
                  f"({r['resolved_by']})")
    print(f"\n{len(rows)} ids checked: " +
          ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if fallback:
        print(f"{len(fallback)} have NO English label in Wikidata and were "
              f"resolved by their English Wikipedia sitelink: "
              + ", ".join(r["display_name"] for r in fallback))
    print(f"wrote {out}")
    if failures:
        print(f"\nFAILED: {len(failures)} roster ids are not the person named.",
              file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
