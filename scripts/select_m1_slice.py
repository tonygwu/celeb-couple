#!/usr/bin/env python3
"""Choose the M1 pairing slice, deterministically, BEFORE anything is judged.

The rule is fixed here and the output records it. Plan v3's cohort was selected
on stated criteria before any check of how easy each person was to score, and
the same discipline applies: a slice picked after seeing results is a slice
picked to flatter them.

THE RULE, in full:

  1. Keep roster members who appear in BOTH domains -- at least one adult-window
     relationship episode AND at least one co-starring film pair. A slice that
     exercises only one board would not validate the path.
  2. Rank them by total pairings, descending. Ties break on Wikidata id, which
     is arbitrary and stable rather than arbitrary and not.
  3. Take the top 5 men and the top 5 women. Gender-balanced because boards 3
     and 4 are mirrors of 1 and 2, and a slice of only men would leave the
     women's boards with one pairing each.
  4. Judge every pairing that touches any of those 10.

Read-only. Spends no quota.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.artifacts import require  # noqa: E402

PER_GENDER = 5


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Pick the M1 pairing slice. Read-only; spends no quota.")
    ap.add_argument("--roster", default="docs/roster-100.json")
    ap.add_argument("--out", default="data/roster100/run/m1_slice.json")
    ap.add_argument("--per-gender", type=int, default=PER_GENDER)
    args = ap.parse_args()

    roster = {p["wikidata_qid"]: p for p in require(REPO, args.roster)["people"]}
    eps = require(REPO, "data/roster100/records/episodes.json")["episodes"]
    films = require(REPO, "data/roster100/records/onscreen_candidates.json")["candidates"]

    rl, os_ = Counter(), Counter()
    for e in eps:
        if not e.get("adult_years"):
            continue
        for q in (e["subject_qid"], e["partner_qid"]):
            if q in roster:
                rl[q] += 1
    for c in films:
        for q in (c["male_qid"], c["female_qid"]):
            if q in roster:
                os_[q] += 1

    both = [q for q in roster if rl[q] and os_[q]]
    # -total first, then the qid: a stable tie-break that is not a judgement.
    ranked = sorted(both, key=lambda q: (-(rl[q] + os_[q]), q))
    focal: list[str] = []
    for gender in ("male", "female"):
        taken = [q for q in ranked
                 if roster[q].get("gender_category") == gender][:args.per_gender]
        focal.extend(taken)
    focal_set = set(focal)

    pairings = []
    for c in films:
        if focal_set & {c["male_qid"], c["female_qid"]}:
            year = (c.get("release") or "")[:4]
            if not year.isdigit():
                continue
            pairings.append({
                "pairing_id": f"pr_screen_{c['work_qid']}_{c['male_qid']}_{c['female_qid']}",
                "domain": "on_screen", "period": year,
                "work": c.get("title"), "work_qid": c.get("work_qid"),
                "male_qid": c["male_qid"], "female_qid": c["female_qid"],
                "male": c.get("male"), "female": c.get("female"),
            })
    for e in eps:
        years = [str(y) for y in (e.get("adult_years") or [])]
        if not years or not (focal_set & {e["subject_qid"], e["partner_qid"]}):
            continue
        a, b = e["subject_qid"], e["partner_qid"]
        ga = (roster.get(a) or {}).get("gender_category")
        male, female = (a, b) if ga == "male" else (b, a)
        # One judgment per EPISODE, not per year. The relationship is the season.
        pairings.append({
            "pairing_id": f"pr_real_{male}_{female}_{years[0]}",
            "domain": "real_life", "period": years[0],
            "period_span": [years[0], years[-1]],
            "work": None, "work_qid": None,
            "male_qid": male, "female_qid": female,
            "male": (roster.get(male) or {}).get("display_name"),
            "female": (roster.get(female) or {}).get("display_name"),
        })

    # Dedupe on pairing_id: a film with two focal actors appears twice above.
    seen, unique = set(), []
    for p in pairings:
        if p["pairing_id"] in seen:
            continue
        seen.add(p["pairing_id"])
        unique.append(p)
    unique.sort(key=lambda p: (p["domain"], p["period"], p["pairing_id"]))

    out = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "selection_rule": (
            "Roster members present in BOTH domains, ranked by total pairings "
            f"descending with ties broken on Wikidata id, top {args.per_gender} "
            "men and top {n} women, then every pairing touching any of them. "
            "Fixed before any judging."
        ).format(n=args.per_gender),
        "focal": [{"qid": q, "name": roster[q]["display_name"],
                   "gender": roster[q].get("gender_category"),
                   "real_life_pairings": rl[q], "on_screen_pairings": os_[q]}
                  for q in focal],
        "counts": {
            "focal_actors": len(focal),
            "pairings_total": len(unique),
            "on_screen": sum(1 for p in unique if p["domain"] == "on_screen"),
            "real_life": sum(1 for p in unique if p["domain"] == "real_life"),
        },
        "pairings": unique,
    }
    dest = REPO / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))

    print(f"focal actors ({len(focal)}):")
    for f in out["focal"]:
        print(f"  {f['name']:<22} {f['gender']:<7} real-life {f['real_life_pairings']:<3} "
              f"on-screen {f['on_screen_pairings']}")
    print(f"\npairings to judge: {out['counts']['pairings_total']} "
          f"({out['counts']['on_screen']} on-screen, {out['counts']['real_life']} real-life)")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
