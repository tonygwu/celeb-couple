#!/usr/bin/env python3
"""Find films where a male and a female roster member both appear in the cast.

These are CANDIDATES and nothing more. Co-appearance in a cast list proves only
that both were in the film; scripts/classify_romance.py decides whether their
characters are a couple, and seventeen of the pilot's first twenty were not.

Existed only as an inline snippet, which is the third stage found that way — the
reports chain fails in a fresh clone with "Missing artifact:
onscreen_candidates.json" and nothing could name the command that makes it.

Read-only. Spends no model quota.
"""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require       # noqa: E402
from modules.records.wikidata import _query, _val   # noqa: E402

#: Films where both a male and a female roster member are credited cast (P161).
#: Q11424 is "film"; the subclass walk catches documentary, animated film, etc.
QUERY = """
SELECT ?film ?filmLabel ?pub ?m ?f WHERE {
  VALUES ?m { %s }
  VALUES ?f { %s }
  ?film wdt:P31/wdt:P279* wd:Q11424 .
  ?film wdt:P161 ?m . ?film wdt:P161 ?f .
  OPTIONAL { ?film wdt:P577 ?pub }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
} LIMIT %d
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cohort", default="docs/pilot-cohort.json")
    ap.add_argument("--limit", type=int, default=400)
    ap.add_argument("--out", default="data/pilot/records/onscreen_candidates.json")
    args = ap.parse_args()

    people = require(REPO, args.cohort)["people"]
    names = {p["wikidata_qid"]: p["display_name"] for p in people}
    men = [p["wikidata_qid"] for p in people if p["gender_category"] == "male"]
    women = [p["wikidata_qid"] for p in people if p["gender_category"] == "female"]
    if not men or not women:
        print(f"cohort has {len(men)} men and {len(women)} women; "
              "an on-screen pairing needs one of each")
        return 1

    rows = _query(QUERY % (" ".join(f"wd:{q}" for q in men),
                           " ".join(f"wd:{q}" for q in women), args.limit))
    seen: dict[tuple, dict] = {}
    rows_missing_ids = 0
    for r in rows:
        film = (_val(r, "film") or "").rsplit("/", 1)[-1]
        m = (_val(r, "m") or "").rsplit("/", 1)[-1]
        f = (_val(r, "f") or "").rsplit("/", 1)[-1]
        if not (film and m and f):
            # A SPARQL row missing one of the three ids is malformed. Dropping
            # it is right; dropping it without a count means the candidate
            # total can shrink with nothing to notice.
            rows_missing_ids += 1
            continue
        seen.setdefault((film, m, f), {
            "work_qid": film, "title": _val(r, "filmLabel") or film,
            "release": (_val(r, "pub") or "")[:10],
            "male_qid": m, "male": names.get(m, m),
            "female_qid": f, "female": names.get(f, f)})

    out = sorted(seen.values(), key=lambda c: (c["release"] or "9999", c["title"]))
    # A label that fell back to its own Q-id is an unresolved name, not a name.
    # Two partners once entered the corpus as bare ids for exactly this reason,
    # and a film table reading "Q194413" tells a reader nothing.
    import re as _re
    unresolved = sorted(
        {v for c in out for k, v in c.items()
         if k in ("title", "male", "female") and _re.fullmatch(r"Q\d+", str(v))})
    if unresolved:
        print(f"  WARNING: {len(unresolved)} label(s) unresolved, shown as "
              f"Q-ids: {', '.join(unresolved)}")
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": "wikidata P161 co-appearance",
        "cohort": args.cohort,
        "status": "UNVERIFIED CANDIDATES",
        "rows_missing_ids": rows_missing_ids,
        "labels_unresolved": unresolved,
        "caveat": ("Co-appearance in a cast list proves only that both were in "
                   "the film. A qualifying on-screen pairing needs an established "
                   "reciprocal romance between their CHARACTERS, which "
                   "scripts/classify_romance.py decides. Seventeen of the "
                   "pilot's first twenty were not romances."),
        "candidates": out,
    }
    dest = REPO / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2))
    print(f"co-starring candidate pairs: {len(out)}")
    for c in out[:8]:
        print(f"  {(c['release'][:4] or '????')}  {c['title'][:34]:34} "
              f"{c['male'][:16]:16} + {c['female'][:16]}")
    if len(out) > 8:
        print(f"  ... and {len(out) - 8} more")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
