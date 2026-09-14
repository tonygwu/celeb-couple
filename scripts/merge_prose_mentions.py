#!/usr/bin/env python3
"""Merge prose mentions into the observation corpus, deduplicating by lineage.

A prose mention of "named People's Sexiest Man Alive in 2018" and the row in
the Sexiest Man Alive table are THE SAME underlying judgment reached by two
routes. Counting both would make one magazine's decision look like two, which
is exactly what the syndication rule exists to prevent.

Dedup key is (person, year, publisher, normalised list name). A mention that
matches an existing observation is dropped and counted, not merged in.
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402
from packages.ids.keys import stable_id                              # noqa: E402

_NOISE = re.compile(r"[^a-z0-9]+")


def _norm_list(name: str) -> str:
    """Collapse 'Sexiest Man Alive' and 'the Sexiest Man Alive' to one key."""
    n = _NOISE.sub(" ", (name or "").lower()).strip()
    for stop in ("the ", "a ", "an "):
        if n.startswith(stop):
            n = n[len(stop):]
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--observations", default="data/pilot/observations/observations.json")
    ap.add_argument("--mentions", default="data/pilot/observations/prose_mentions.json")
    ap.add_argument("--out", default="data/pilot/observations/observations.json")
    args = ap.parse_args()

    _abs = lambda rel: Path(rel) if Path(rel).is_absolute() else REPO / rel
    obs = (json.loads(Path(args.observations).read_text())
           if Path(args.observations).is_absolute()
           else require(REPO, args.observations))
    mentions = require(REPO, args.mentions)["mentions"]
    editions = {e["list_edition_id"]: e for e in obs["editions"]}

    # Dedup key deliberately IGNORES the list name: same person, same year, same
    # publisher is presumed to be one judgment.
    #
    # Measured 2026-09-14: keying on the list name too let "PEOPLE / Most
    # Beautiful cover choice 1990" and "People / Most Beautiful People in the
    # World 1990" both survive, which made ONE magazine's decision about ONE
    # person in ONE year look like two independent publishers. That is precisely
    # what the syndication rule exists to prevent, and the rubric's bands count
    # independent publications.
    #
    # The cost is that a publisher running two genuinely different lists in one
    # year about the same person collapses to one observation. That is the safe
    # direction to be wrong in.
    existing = set()
    for o in obs["observations"]:
        ed = editions.get(o["list_edition_id"], {})
        existing.add((o["person_id"], o["concerns_period"],
                      (ed.get("publisher") or "").strip().lower()))

    added, dup_existing, dup_within = [], 0, 0
    seen_mentions = set()
    new_editions = []
    for m in mentions:
        key = (m["person_id"], str(m["year"]), m["publisher"].strip().lower())
        if key in seen_mentions:
            dup_within += 1
            continue
        seen_mentions.add(key)
        if key in existing:
            dup_existing += 1
            continue
        eid = stable_id("le", "prose", m["publisher"], m["list_name"], str(m["year"]))
        new_editions.append({
            "list_edition_id": eid, "publisher": m["publisher"],
            "title": f"{m['list_name']} {m['year']}",
            "published_at": str(m["year"]), "published_precision": "year",
            "concerns_period": str(m["year"]),
            "candidate_set_described": (
                f"as described by the publisher; recorded from a biographical "
                f"mention rather than from the list itself, so the pool is "
                f"whatever {m['publisher']} used and is not further specified"),
            "list_length": m.get("list_length"),
            "attribution": "Fact reported by English Wikipedia in the subject's article",
            "licence": "CC BY-SA 4.0 (Wikipedia); the selection is the publisher's",
            "content_sha256": m["article_sha256"],
        })
        observed = {}
        if m["shape"] == "ordered_rank":
            # None, never a plausible-looking default: an invented depth is
            # the fact that decides how selective the placement was.
            observed = {"rank": m["rank"], "list_length": m.get("list_length"),
                        "order_is_ranking": True,
                        "order_basis": "the article states an explicit position"}
        elif m["shape"] == "editorial_award":
            observed = {"award_name": m["list_name"], "winner": True}
        else:
            # None, never 0: an unstated size is unknown, not empty
            observed = {"list_length": m.get("list_length")}
        added.append({
            "observation_id": stable_id("obs", eid, m["person_id"]),
            "person_id": m["person_id"], "list_edition_id": eid,
            "evidence_type": m["shape"], "observed": observed,
            "concerns_period": str(m["year"]), "published_at": str(m["year"]),
            "excerpt": m["evidence"][:240],
            "excerpt_locator": "biographical article prose",
            "lineage": {"original_source": eid, "is_syndicated_copy": False},
            "review_status": "pending",
        })

    obs["editions"].extend(new_editions)
    obs["observations"].extend(added)
    obs.setdefault("merges", []).append({
        "from": "prose_mentions", "mentions_in": len(mentions),
        "added": len(added), "duplicate_of_existing_observation": dup_existing,
        "duplicate_within_mentions": dup_within,
        "dedup_key": "person + year + publisher (list name deliberately ignored)",
        "note": ("A prose mention of an award and the award table row are one "
                 "judgment reached two ways; counting both would make one "
                 "magazine's decision look like two. The key ignores the list "
                 "name because the same franchise gets described differently in "
                 "a table title and in prose."),
    })
    # Recompute the derived coverage block. It is written by fetch_observations
    # and was going stale the moment anything merged in: the scaling table read
    # 27 observations from it while the file held 35.
    from collections import Counter
    ed = {e["list_edition_id"]: e for e in obs["editions"]}
    per_person = Counter(o["person_id"] for o in obs["observations"])
    cov = obs.setdefault("coverage", {})
    cov["total_observations"] = len(obs["observations"])
    cov["per_person"] = dict(per_person.most_common())
    # Cohort-only, same correction as fetch_observations. `per_person` counts
    # partners too, and against a cohort denominator that read as full
    # coverage while five cohort members had nothing.
    _cohort_total = cov.get("cohort_people_total")
    _cohort_none = set(cov.get("people_with_none") or [])
    if _cohort_total is not None:
        cov["cohort_people_with_any_observation"] = _cohort_total - len(_cohort_none)
    cov["people_with_observations_including_partners"] = len(per_person)
    cov["recomputed_after_merge"] = True

    _abs(args.out).write_text(json.dumps(obs, indent=2))
    print(f"mentions in: {len(mentions)}  added: {len(added)}  "
          f"dup vs existing: {dup_existing}  dup within mentions: {dup_within}")
    for a in added:
        ed = next(e for e in new_editions if e["list_edition_id"] == a["list_edition_id"])
        print(f"  + {a['person_id']:10} {a['concerns_period']} {ed['publisher'][:18]:18} "
              f"{a['evidence_type']}")
    print(f"wrote {_abs(args.out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
