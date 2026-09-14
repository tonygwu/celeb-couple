#!/usr/bin/env python3
"""Check the corpus against the live Wikipedia pages it came from.

The grounding audit checks whether a RATIONALE is supported by its
observations. Nothing checked whether the OBSERVATIONS are supported by their
sources. Every conclusion in this project rests on 41 rows extracted by two
parsers and one model, and until this existed all three were trusted.

For each observation it re-fetches the section it came from and asks whether
the same person really holds that rank or award in that year. Prose-extracted
mentions are checked differently: their excerpt must still appear verbatim in
the article, which is the only claim they make.

Hits the network, so it is NOT in the chain. Run it when the corpus changes, or
when a conclusion is about to be relied on. It spends no model quota.
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
from packages.llmkit.artifacts import require                      # noqa: E402
from modules.consensus.wikipedia_lists import fetch_section_wikitext  # noqa: E402

USER_AGENT = (
    "celeb-couple-M0/0.1 (https://github.com/tonygwu/celeb-couple; read-only research)"
)
#: Where each publisher's table lives. Kept beside fetch_observations.py's own
#: source list; a publisher absent here is reported as unverifiable, never as
#: verified.
TABLES = {
    "PEOPLE": [("People (magazine)", 4), ("People (magazine)", 9)],
    "Maxim": [("Maxim (magazine)", 6)],
    "Esquire": [("Esquire (magazine)", 6)],
    "FHM": [("FHM's 100 Sexiest Women (UK)", 2)],
}


def ordinal_suffix(n: int) -> str:
    """The English ordinal suffix for ``n``.

    A dict of {2: "nd", 3: "rd"} defaulting to "th" was here first and is
    wrong from 21 upward: it searched for "21th" and found nothing, which this
    file would have reported as "not found in the source table". Wikipedia
    carries only each edition's top ten, so nothing in the corpus reaches 21
    today and the bug was invisible. It would appear the first time a deeper
    source is added, as an unverifiable row rather than an error.
    """
    if 11 <= n % 100 <= 13:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def article_text(title: str, timeout: int = 60) -> str:
    url = ("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
        {"action": "query", "prop": "extracts", "explaintext": "1",
         "format": "json", "titles": title}))
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as fh:
        pages = json.load(fh)["query"]["pages"]
    return next(iter(pages.values())).get("extract") or ""


def name_at(block: str, rank: int) -> str | None:
    """Who the wikitext block puts at ``rank``."""
    if rank == 1:
        m = re.search(r"'''\[\[([^\]|]+)", block)
        return m.group(1) if m else None
    suffix = ordinal_suffix(rank)
    m = re.search(rf"\b{rank}{suffix}:\s*\[\[([^\]|]+)", block)
    return m.group(1) if m else None


def main() -> int:
    # Names must match EXACTLY. A surname comparison was tried first and is
    # wrong here: "Denzel Washington" would match "Pauletta Pearson Washington",
    # and this file's whole job is catching a wrong person in a row. All 33
    # table-sourced rows match in full, so exactness costs nothing. A future
    # piped link or redirect will report "not found in the source table", which
    # is a prompt to look rather than a silent pass.
    ap = argparse.ArgumentParser(
        description=("Re-check every observation against the live Wikipedia "
                     "page it came from. Hits the network; spends no quota."))
    ap.add_argument("--out", default="data/pilot/run/observation_verification.json")
    args = ap.parse_args()

    obs = require(REPO, "data/pilot/observations/observations.json")
    editions = {e["list_edition_id"]: e for e in obs["editions"]}
    names = {p["wikidata_qid"]: p["display_name"]
             for p in require(REPO, "docs/pilot-cohort.json")["people"]
             + require(REPO, "data/pilot/records/partner_universe.json")["people"]}

    sections: dict[tuple[str, int], str] = {}
    rows, unverifiable = [], []

    for o in obs["observations"]:
        ed = editions[o["list_edition_id"]]
        pub = ed.get("publisher", "")
        who = names.get(o["person_id"], o["person_id"])

        if o["excerpt_locator"] == "biographical article prose":
            text = article_text(who)
            ok = _norm(o["excerpt"]) in _norm(text)
            rows.append({"observation_id": o["observation_id"], "person": who,
                         "period": o["concerns_period"], "kind": "prose",
                         "verified": ok,
                         "detail": "excerpt found verbatim in the article" if ok
                                   else "excerpt NOT found in the live article"})
            continue

        pages = TABLES.get(pub)
        if not pages:
            unverifiable.append({"observation_id": o["observation_id"],
                                 "publisher": pub,
                                 "why": "no table location recorded for this publisher"})
            continue

        found = None
        for page, sec in pages:
            if (page, sec) not in sections:
                sections[(page, sec)] = fetch_section_wikitext(page, sec)[0]
            wt = sections[(page, sec)]
            for block in wt.split("\n|-"):
                if not re.search(rf"\b{re.escape(o['concerns_period'])}\b", block):
                    continue
                rank = o["observed"].get("rank")
                got = name_at(block, rank) if rank else None
                if got is None and rank is None:
                    m = re.search(r"\[\[([^\]|]+)", block)
                    got = m.group(1) if m else None
                if got and got == who:
                    found = got
                    break
            if found:
                break
        rows.append({"observation_id": o["observation_id"], "person": who,
                     "period": o["concerns_period"],
                     "kind": o["evidence_type"], "verified": bool(found),
                     "detail": (f"source names {found}" if found
                                else "not found in the source table")})

    verified = sum(1 for r in rows if r["verified"])
    payload = {
        "checked": len(rows), "verified": verified,
        "not_verified": [r for r in rows if not r["verified"]],
        "unverifiable": unverifiable,
        "rows": rows,
        "note": ("A row that could not be verified is NOT evidence the "
                 "observation is wrong: Wikipedia carries only the top ten of "
                 "FHM's hundred, so a deeper prose-sourced rank has no table "
                 "row to match against. Read the detail."),
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")

    for r in rows:
        mark = "OK  " if r["verified"] else "CHECK"
        print(f"  {mark} {r['person'][:22]:22} {r['period']:5} "
              f"{r['kind'][:16]:16} {r['detail']}")
    print(f"\n{verified} of {len(rows)} observations verified against the live "
          f"source; {len(unverifiable)} had no table location recorded.")
    print(f"wrote {out}")

    # Non-zero on a break, like verify_trap.py and audit_doc_numbers.py. A row
    # that stops matching is NOT proof the observation was always wrong: an
    # editor may have renamed a link or restructured the table. It does mean a
    # human has to look before any document keeps claiming the corpus was
    # confirmed against its sources. Silence here would let that sentence
    # outlive the fact.
    broken = len(payload["not_verified"]) + len(unverifiable)
    if broken:
        print(f"\nFAILED: {broken} observation(s) no longer match their "
              f"source. Read {out} before trusting any document that says the "
              f"corpus was verified.", file=sys.stderr)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
