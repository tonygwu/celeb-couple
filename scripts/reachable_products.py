#!/usr/bin/env python3
"""What CAN be built with the evidence that exists?

The pairing board needs two people judged near the same year by the same kind
of evidence, and the source hunt concluded that no permitted source supplies the
depth for that. Stopping there would leave the operator a dead end instead of a
decision.

So this measures each alternative against the SAME corpus, and reports what
each would actually contain. It recommends nothing: each option trades away
something different, and which trade is acceptable is not an engineering call.

Read-only. Spends no model quota.
"""
from __future__ import annotations
import argparse, json, sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", default="data/roster100/run/reachable.json")
    ap.add_argument("--out-md", default="docs/REACHABLE-PRODUCTS.md")
    args = ap.parse_args()

    obs = require(REPO, "data/roster100/observations/observations.json")
    eps = require(REPO, "data/roster100/records/episodes.json")
    joint = require(REPO, "data/roster100/run/joint_real_life.json")
    roster = require(REPO, "docs/roster-100.json")["people"]
    names = {p["wikidata_qid"]: p["display_name"] for p in roster}
    gender = {p["wikidata_qid"]: p["gender_category"] for p in roster}
    editions = {e["list_edition_id"]: e for e in obs["editions"]}

    per_person = Counter(o["person_id"] for o in obs["observations"])
    years_of = defaultdict(set)
    pubs_of = defaultdict(set)
    for o in obs["observations"]:
        years_of[o["person_id"]].add(o["concerns_period"])
        pubs_of[o["person_id"]].add(
            (editions[o["list_edition_id"]]["publisher"] or "").strip().lower())

    in_roster = {q for q in per_person if q in names}
    multi_year = {q for q in in_roster if len(years_of[q]) >= 2}
    multi_pub = {q for q in in_roster if len(pubs_of[q]) >= 2}
    span = {q: (min(years_of[q]), max(years_of[q])) for q in multi_year}

    scorable_eps = [e for e in eps["episodes"] if e["scorable"] and e.get("adult_years")]
    one_sided = sum(
        1 for e in scorable_eps
        if (e["subject_qid"] in per_person) != (e["partner_qid"] in per_person))

    options = [
        {
            "name": "A. The pairing board, as specified",
            "unit": "pairings with both sides scored, same evidence shape",
            "count": joint["comparability"].get("comparable", 0),
            "of": len(scorable_eps),
            "verdict": "Not reachable. One comparable pairing across 239 episodes.",
            "gives_up": "nothing",
        },
        {
            "name": "B. Pairing board, comparability caveat shown instead of enforced",
            "unit": "pairings with both sides scored, any shapes",
            "count": joint["jointly_covered_within_1y"],
            "of": len(scorable_eps),
            "verdict": "Five rows. Four of them compare an award against a list "
                       "placement, so most of the board would be measuring "
                       "publication format.",
            "gives_up": "the claim that a gap is about the two people",
        },
        {
            "name": "C. Recognition timeline per person",
            "unit": "people with two or more judged years",
            "count": len(multi_year),
            "of": len(roster),
            "verdict": "Reachable now. Shows when each person was recognised, by "
                       "whom, with the evidence — and never compares two people.",
            "gives_up": "the pairing idea entirely; there is no WAR and no gap",
        },
        {
            "name": "D. Standing leaderboard, no pairings",
            "unit": "people with two or more independent publishers",
            "count": len(multi_pub),
            "of": len(roster),
            "verdict": "Reachable but thin, and it ranks people by how much "
                       "coverage they got, which is closer to fame than to "
                       "appearance.",
            "gives_up": "the pairing idea, and it inherits the shape confound "
                        "directly into the ranking",
        },
        {
            "name": "E. One-sided pairing view",
            "unit": "episodes where exactly one partner is judged",
            "count": one_sided,
            "of": len(scorable_eps),
            "verdict": "Large, and it cannot produce a gap: a gap needs two "
                       "estimates. It could show 'who was recognised while with "
                       "whom', which is a different claim.",
            "gives_up": "the signed gap, the mirroring, and the WAR metric",
        },
    ]

    payload = {"options": options,
               "corpus": {"observations": len(obs["observations"]),
                          "roster_people_with_evidence": len(in_roster),
                          "roster": len(roster),
                          "scorable_episodes": len(scorable_eps)},
               "note": "This recommends nothing. Each option trades away something "
                       "different and which trade is acceptable is not an "
                       "engineering decision."}
    (REPO / args.out_json).parent.mkdir(parents=True, exist_ok=True)
    (REPO / args.out_json).write_text(json.dumps(payload, indent=2))

    L = ["# What is reachable with the evidence that exists", "",
         "Generated by `scripts/reachable_products.py` from the 100-roster "
         "corpus. `docs/SOURCE-HUNT.md` concluded that the pairing board's "
         "source requirement cannot be met on a permitted route. Rather than "
         "leave that as a dead end, this measures each alternative against the "
         "same corpus.", "",
         f"Corpus: {payload['corpus']['observations']} observations over "
         f"{payload['corpus']['roster_people_with_evidence']} of "
         f"{payload['corpus']['roster']} roster people, and "
         f"{payload['corpus']['scorable_episodes']} scorable relationship "
         f"episodes.", "",
         "| Option | Unit | Count | Gives up |", "|---|---|---|---|"]
    for o in options:
        L.append(f"| {o['name']} | {o['unit']} | **{o['count']}** of {o['of']} | "
                 f"{o['gives_up']} |")
    L += ["", "## Reading each one", ""]
    for o in options:
        L += [f"### {o['name']}", "", o["verdict"], ""]
    L += ["## The decision this leaves you", "",
          "Option A is the product as specified and it is not reachable. "
          "Everything else trades away part of the original idea: B keeps the "
          "board and loses the claim that a gap is about two people; C and D "
          "keep the evidence and lose the pairing; E keeps the pairing and loses "
          "the gap.", "",
          f"*{payload['note']}*"]
    (REPO / args.out_md).write_text("\n".join(L) + "\n")
    for o in options:
        print(f"  {o['name'][:52]:52} {o['count']:>4} of {o['of']}")
    print(f"\nwrote {REPO / args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
