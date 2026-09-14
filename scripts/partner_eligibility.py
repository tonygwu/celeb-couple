#!/usr/bin/env python3
"""Split the partner universe into 'no evidence found' and 'never rate'.

The plan says: do not rate private individuals merely because they dated a
celebrity, and account for those exclusions in coverage. That makes the 22
pairings missing a side two very different populations:

  - a public entertainment figure with no evidence FOUND, which is a gap the
    project could close with better sources, and
  - someone who is simply not a public figure in the relevant sense, whom the
    project must NOT rate at any coverage level.

Reporting them together overstates how much of the board is reachable. Read-only.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402
from modules.records.wikidata import _query, _val                    # noqa: E402

#: Occupations that put someone in front of an audience on their appearance,
#: which is the population attractiveness lists draw from.
PUBLIC_FACING = {
    "actor", "film actor", "television actor", "stage actor", "voice actor",
    "model", "singer", "musician", "rapper", "dancer", "presenter",
    "television presenter", "comedian", "entertainer", "performing artist",
    "recording artist", "singer-songwriter", "fashion model", "athlete",
}

Q = """
SELECT ?p ?pLabel ?occLabel ?article WHERE {
  VALUES ?p { %s }
  OPTIONAL { ?p wdt:P106 ?occ }
  OPTIONAL { ?article schema:about ?p ; schema:isPartOf <https://en.wikipedia.org/> }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/pilot/records/partner_eligibility.json")
    args = ap.parse_args()

    universe = require(REPO, "data/pilot/records/partner_universe.json")["people"]
    obs = require(REPO, "data/pilot/observations/observations.json")
    have = {o["person_id"] for o in obs["observations"]}
    qids = [p["wikidata_qid"] for p in universe]

    rows = _query(Q % " ".join(f"wd:{q}" for q in qids))
    info: dict[str, dict] = {}
    for r in rows:
        qid = (_val(r, "p") or "").rsplit("/", 1)[-1]
        d = info.setdefault(qid, {"occupations": set(), "article": None})
        occ = _val(r, "occLabel")
        if occ and not occ.startswith("Q"):
            d["occupations"].add(occ.lower())
        if _val(r, "article"):
            d["article"] = _val(r, "article")

    out = []
    for p in universe:
        qid = p["wikidata_qid"]
        d = info.get(qid, {"occupations": set(), "article": None})
        occs = sorted(d["occupations"])
        public_facing = bool(d["occupations"] & PUBLIC_FACING)
        has_article = bool(d["article"])
        if qid in have:
            status = "evidenced"
        elif public_facing:
            status = "public_figure_no_evidence_found"
        elif has_article:
            status = "notable_but_not_public_facing"
        else:
            status = "not_a_public_figure_do_not_rate"
        out.append({"name": p["display_name"], "qid": qid, "status": status,
                    "occupations": occs, "has_enwiki_article": has_article})

    counts: dict[str, int] = {}
    for r in out:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    reachable = counts.get("evidenced", 0) + counts.get(
        "public_figure_no_evidence_found", 0)
    payload = {
        "partners": len(out), "counts": counts,
        "reachable_ceiling": reachable,
        "never_rate": len(out) - reachable,
        "reading": (
            f"{len(out) - reachable} of {len(out)} partners are people this "
            "project must not rate: the plan forbids rating a private individual "
            "merely because they dated a celebrity. Those pairings are a "
            "PERMANENT exclusion, not a coverage gap, and counting them in the "
            "denominator overstates how much of the board is reachable."
        ),
        "partners_detail": sorted(out, key=lambda r: (r["status"], r["name"])),
    }
    (REPO / args.out).write_text(json.dumps(payload, indent=2))
    print(json.dumps(counts, indent=2))
    print(f"\nreachable ceiling: {reachable} of {len(out)} partners\n")
    for r in payload["partners_detail"]:
        print(f"  {r['status']:34} {r['name'][:26]:26} {', '.join(r['occupations'][:3])}")
    print(f"\nwrote {REPO / args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
