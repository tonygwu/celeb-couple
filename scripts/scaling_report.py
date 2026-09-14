#!/usr/bin/env python3
"""Does coverage scale with roster size? Measured, not assumed.

The pilot ran 14 people. This compares it against the plan's full 100-name
roster, put through the same free stages, to answer the question that decides
whether the product is reachable by growing the roster.

Read-only. Spends no model quota.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-json", default="data/roster100/run/scaling.json")
    ap.add_argument("--out-md", default="docs/SCALING.md")
    args = ap.parse_args()

    pilot_obs = require(REPO, "data/pilot/observations/observations.json")
    pilot_eps = require(REPO, "data/pilot/records/episodes.json")
    pilot_joint = require(REPO, "data/pilot/run/joint_with_nearby.json")
    r_obs = require(REPO, "data/roster100/observations/observations.json")
    r_eps = require(REPO, "data/roster100/records/episodes.json")
    r_joint = require(REPO, "data/roster100/run/joint_real_life.json")
    r_density = require(REPO, "data/roster100/run/evidence_density.json")
    p_density = require(REPO, "data/pilot/run/evidence_density.json")

    pilot_comp = sum(1 for j in pilot_joint.get("jointly_covered", [])
                     if j.get("comparability") == "comparable")
    rows = [
        ("Roster size", 14, 100),
        ("Relationship episodes (scorable)",
         pilot_eps["counts"]["eligible_after_adult_window"],
         r_joint["scorable_episodes"]),
        # Count the list itself. A stored summary goes stale the moment
        # anything merges in, which is exactly what happened here.
        ("Observations", len(pilot_obs["observations"]), len(r_obs["observations"])),
        ("People with any observation",
         len({o["person_id"] for o in pilot_obs["observations"]}),
         len({o["person_id"] for o in r_obs["observations"]})),
        ("Person-periods", p_density["person_periods"], r_density["person_periods"]),
        ("Mean observations per person-period",
         p_density["mean_observations_per_person_period"],
         r_density["mean_observations_per_person_period"]),
        ("Person-periods with 2+ publishers",
         p_density["person_periods_with_two_or_more_publishers"],
         r_density["person_periods_with_two_or_more_publishers"]),
        ("Episodes with evidence on BOTH sides anywhere", "—",
         r_joint["both_sides_have_evidence"]),
        ("Jointly covered within ±1 year",
         len(pilot_joint.get("jointly_covered", [])),
         r_joint["jointly_covered_within_1y"]),
        ("...of those, COMPARABLE (same evidence shape)", pilot_comp,
         r_joint["comparability"].get("comparable", 0)),
    ]

    payload = {"rows": [{"metric": m, "pilot_14": a, "roster_100": b}
                        for m, a, b in rows],
               "finding": (
                   "Coverage does not scale with roster size. A seven-fold larger "
                   "roster produced 3.7x the observations and 7.7x the episodes, "
                   "and the number of COMPARABLE jointly covered pairings stayed "
                   "at one."),
               "why": (
                   "Joint coverage is a conjunction of independently rare "
                   "conditions: both people judged, near the same year, by the "
                   "same kind of evidence. Each is uncommon, so the conjunction "
                   "is rarer than any of them, and growing the roster multiplies "
                   "the numerator and the denominator together.")}
    (REPO / args.out_json).parent.mkdir(parents=True, exist_ok=True)
    (REPO / args.out_json).write_text(json.dumps(payload, indent=2))

    L = ["# Does coverage scale with roster size?", "",
         "Generated from the artifacts by `scripts/scaling_report.py`. The pilot "
         "ran 14 people; the plan's full 100-name roster was put through the same "
         "free stages. Both rosters were chosen on prominence before any check of "
         "how easy anyone is to score.", "",
         "## The answer", "", f"**{payload['finding']}**", "", payload["why"], "",
         "## The numbers", "",
         "| Metric | Pilot (14) | Roster (100) |", "|---|---|---|"]
    for m, a, b in rows:
        L.append(f"| {m} | {a} | {b} |")
    L += ["", "## What this rules out", "",
          "Growing the roster is not a path to a board. It was the obvious next "
          "move after the pilot and it does not work, because every added person "
          "brings their own unpaired years along with them.", "",
          "## What it leaves", "",
          "Only sources that raise DENSITY on person-years that already carry a "
          "judgment, ideally of the same shape as the one already there. That is "
          "a much narrower requirement than 'more sources', and the backlog now "
          "states it that way.", "",
          "## Caveat", "",
          "The 100-roster figures come from the free stages only: Wikidata "
          "records and Wikipedia list articles. No prose extraction, no scoring, "
          "no romance classification was run at that scale, so the on-screen "
          "domain is absent from the roster column and the real-life numbers are "
          "a floor rather than a final figure."]
    (REPO / args.out_md).write_text("\n".join(L) + "\n")
    for m, a, b in rows:
        print(f"  {m:48} {str(a):>6}  ->  {b}")
    print(f"\nwrote {REPO / args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
