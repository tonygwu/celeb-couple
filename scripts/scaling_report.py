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
    pilot_cohort = require(REPO, "docs/pilot-cohort.json")
    r_cohort = require(REPO, "docs/roster-100.json")

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
        # Labelled just "People with any observation", it counted roster
        # members AND partners. docs/REACHABLE-PRODUCTS.md says "49 of 100
        # roster people" from the same corpus this row called 61, and a reader
        # comparing the two documents sees a contradiction that is really two
        # different denominators wearing one label. Both are reported.
        ("People with any observation (incl. partners)",
         len({o["person_id"] for o in pilot_obs["observations"]}),
         len({o["person_id"] for o in r_obs["observations"]})),
        ("...of those, on the roster itself",
         len({o["person_id"] for o in pilot_obs["observations"]}
             & {p["wikidata_qid"] for p in pilot_cohort["people"]}),
         len({o["person_id"] for o in r_obs["observations"]}
             & {p["wikidata_qid"] for p in r_cohort["people"]})),
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

    # The ratios were typed. The pilot corpus has grown since -- 41
    # observations where the sentence assumed 35, 28 episodes where it assumed
    # 27 -- so "3.7x the observations and 7.7x the episodes" drifted while the
    # table beside it stayed correct. Derive them from the same rows.
    _by_metric = {m: (a, b) for m, a, b in rows}

    def _ratio(metric: str) -> str:
        a, b = _by_metric.get(metric, (None, None))
        if not a or not b or not isinstance(a, (int, float)):
            return "?"
        return f"{b / a:.1f}x"

    _pilot_n, _roster_n = _by_metric.get("Roster size", (None, None))
    _comparable = _by_metric.get(
        "...of those, COMPARABLE (same evidence shape)", (None, None))

    payload = {"rows": [{"metric": m, "pilot_14": a, "roster_100": b}
                        for m, a, b in rows],
               "finding": (
                   f"Coverage does not scale with roster size. A "
                   f"{(_roster_n / _pilot_n):.0f}-fold larger roster produced "
                   f"{_ratio('Observations')} the observations and "
                   f"{_ratio('Relationship episodes (scorable)')} the episodes, "
                   f"and the number of COMPARABLE jointly covered pairings "
                   f"went from {_comparable[0]} to {_comparable[1]}."),
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
    # The source-requirement ladder used to be hand-appended to this file, and
    # this generator rewrites the file from scratch -- so running it silently
    # deleted the section, which is why it was never put in the chain. Render
    # it from the artifact instead, so the generator owns the whole document.
    req_path = REPO / "data/roster100/run/source_requirement.json"
    if req_path.exists():
        req = json.loads(req_path.read_text())
        L += ["", "## What a source would have to look like", "",
              "\"Find better sources\" is not a specification, so "
              "`scripts/source_requirement.py` turns it into one: simulate a "
              "hypothetical annual ranked list over the REAL episode structure "
              f"and the REAL roster, and count how many of the "
              f"{req['episodes_simulated']} scorable episodes come out jointly "
              "covered.", "",
              "| Names per year | p10 | median | p90 |", "|---|---|---|---|"]
        for rung in req["ladder"]:
            L.append(f"| {rung['names_per_year']} | {rung['p10']} | "
                     f"{rung['median_covered']} | {rung['p90']} |")
        peak = max(r["median_covered"] for r in req["ladder"])
        at_peak = min(r["names_per_year"] for r in req["ladder"]
                      if r["median_covered"] == peak)
        one = next((r["median_covered"] for r in req["ladder"]
                    if r["names_per_year"] == 1), None)
        # The reality table was hand-written and lost when this generator
        # first took the file over. It is a claim about what the world
        # publishes rather than a measurement, so it lives here as text and
        # survives regeneration.
        L += ["", "Read against what actually exists:", "",
              "| Source | Names per year |", "|---|---|",
              "| Sexiest Man Alive | 1 |",
              "| People Most Beautiful cover | 1 |",
              "| Maxim Hot 100, as published on Wikipedia | 1 |",
              "| FHM top ten, as on Wikipedia | 10 |",
              "| FHM full list, **not available on a permitted route** | 100 |"]
        L += ["",
              f"**One name a year covers {'nothing' if one == 0 else one}.** "
              "Every award source this project can currently reach sits on that "
              "rung. That is not a shortfall to be closed by adding more such "
              "sources.", "",
              f"**The requirement is about {at_peak} names a year.** At that "
              f"depth the median reaches {peak} episodes. That is the shape of "
              "FHM's real published list, which exists and is not reachable: "
              "Wikipedia carries only its top ten, and the publisher blocks the "
              "AI crawlers.", "",
              f"**It saturates there.** Beyond {at_peak} names a year the median "
              f"stays at {peak}, because the binding constraint becomes the "
              "roster and the era span rather than the list depth. So the "
              f"ceiling for this design, with a perfect source, is "
              f"{peak} of {req['episodes_simulated']} episodes — "
              f"{round(100 * peak / req['episodes_simulated'])} percent — before "
              "the shape-comparability filter cuts it further.", "",
              f"*{req['caveat']}*"]

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
