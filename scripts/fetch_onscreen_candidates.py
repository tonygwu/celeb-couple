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
SELECT ?film ?filmLabel ?pub ?prec ?m ?f WHERE {
  VALUES ?m { %s }
  VALUES ?f { %s }
  ?film wdt:P31/wdt:P279* wd:Q11424 .
  ?film wdt:P161 ?m . ?film wdt:P161 ?f .
  OPTIONAL {
    ?film p:P577/psv:P577 ?node .
    ?node wikibase:timeValue ?pub ; wikibase:timePrecision ?prec .
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
} LIMIT %d
"""

#: Wikidata time precision codes, as used everywhere else in this project.
_YEAR, _MONTH, _DAY = 9, 10, 11


def format_release(value: str, precision: int) -> str:
    """Render a Wikidata time at the precision the SOURCE asserts.

    The old code took `wdt:P577` and sliced the literal to ten characters, so a
    year-precision statement -- which Wikidata serialises as
    `+2002-01-01T00:00:00Z` with precision 9 -- was stored as `2002-01-01`.
    Eleven of twenty films carried that invented January 1st, in a project
    whose `packages/temporal/dates.py` exists specifically to stop a year
    becoming a day and whose test list names "Year-precision date: never
    becomes January 1".
    """
    if precision <= _YEAR:
        return value[:4]
    if precision == _MONTH:
        return value[:7]
    return value[:10]


def choose_release(values: list[tuple[str, int]]) -> tuple[str, int] | None:
    """Pick one publication date from the several Wikidata usually holds.

    P577 is repeated per country, so a film routinely carries four or more
    dates. The old code kept whichever SPARQL row arrived first, which is
    arbitrary and not stable between runs.

    A YEAR-precision statement wins when one exists. That looks backwards --
    preferring the vaguer value -- and it is the honest choice: the
    day-precision values are individual countries' releases, and picking one
    of them silently declares a country. Deconstructing Harry shows the cost of
    the alternative. Its values are 1997 (year) and 1998-05-21 (day); the film
    opened in December 1997, so taking the finest available date would have
    moved it into the wrong YEAR, and the year is what every consumer reads.

    With no year statement, the year MOST of the statements agree on wins, and
    the earliest date within that year is taken. Plain "earliest" was tried
    first and is not safe: Thor: Love and Thunder carries eight dates, two of
    them in 2021 against six in 2022, and earliest-wins moved a 2022 film to
    2021. A majority over the source's own repeated statements is stable
    against a stray value in a way that a single extreme is not.

    A tie between two years goes to the earlier one, so the result does not
    depend on iteration order.
    """
    if not values:
        return None
    years = [v for v in values if v[1] <= _YEAR]
    if years:
        return min(years)
    from collections import Counter
    counts = Counter(v[0][:4] for v in values)
    best = max(counts, key=lambda y: (counts[y], -int(y)))
    return min(v for v in values if v[0][:4] == best)


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
    pubs: dict[tuple, set] = {}
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
        key = (film, m, f)
        pub, prec = _val(r, "pub"), _val(r, "prec")
        if pub and prec is not None:
            pubs.setdefault(key, set()).add((pub, int(prec)))
        seen.setdefault(key, {
            "work_qid": film, "title": _val(r, "filmLabel") or film,
            "male_qid": m, "male": names.get(m, m),
            "female_qid": f, "female": names.get(f, f)})

    multi = 0
    for key, c in seen.items():
        vals = sorted(pubs.get(key, ()))
        if len(vals) > 1:
            multi += 1
        picked = choose_release(vals)
        c["release"] = format_release(*picked) if picked else ""
        c["release_precision"] = (
            {9: "year", 10: "month", 11: "day"}.get(picked[1], "year")
            if picked else None)
        # Kept so a reader can see what was NOT chosen. P577 is repeated per
        # country and the choice is a rule, not a fact.
        c["release_candidates"] = [format_release(v, p) for v, p in vals]

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
                   # "Seventeen of the pilot's first twenty were not romances"
                   # was true before the cast fix taught the classifier which
                   # characters the actors play, when only three qualified.
                   # Eight do now. The count lives in romance.json, which this
                   # script does not read and must not restate.
                   "scripts/classify_romance.py decides. Most co-starring "
                   "pairs are not romances; the current count is in "
                   "data/pilot/records/romance.json."),
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
