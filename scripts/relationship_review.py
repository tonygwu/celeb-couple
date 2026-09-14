#!/usr/bin/env python3
"""Build the human review sheet for real-life relationship claims.

The plan keeps FULL human review of real-life factual claims: "the workload is
reduced by the scope caps, never by relaxing the factual standard." Every
report in this repository labels every relationship an UNVERIFIED candidate,
and until tonight there was a sheet for reviewing RATIONALES and none for
reviewing the claims themselves.

This does not decide anything. It lays each claim beside what Wikidata actually
states -- the relationship type, the dates and their precision, and whether the
statement carries a reference at all -- so a person can confirm or reject it.

Load-bearing episodes come first, exactly as in the grounding sheet: an episode
that feeds a jointly covered pairing carries a published gap, and the rest
carry none.

Read-only. Spends no model quota.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402


def _date(d: dict | None) -> str:
    if not d:
        return "—"
    return f"{d['value']} ({d['precision']})"


def build(episodes: dict, joint: dict | None) -> tuple[list[dict], set[str]]:
    """Return (rows, load_bearing_pair_keys)."""
    load_bearing: set[str] = set()
    if joint:
        for j in joint.get("jointly_covered", []):
            if j.get("domain") == "real_life":
                load_bearing.add("|".join(sorted((j["a"], j["b"]))))

    rows = []
    for ep in episodes["episodes"]:
        names = "|".join(sorted((ep["subject_name"], ep["partner_label"])))
        rows.append({
            "episode_id": ep["episode_id"],
            "subject": ep["subject_name"],
            "subject_qid": ep["subject_qid"],
            "partner": ep["partner_label"],
            "partner_qid": ep["partner_qid"],
            "stages": ep["stages"],
            "start": _date(ep.get("start")),
            "end": "ongoing" if ep.get("ongoing") else _date(ep.get("end")),
            "has_reference": ep.get("has_reference", False),
            "scorable": ep.get("scorable", False),
            "defects": ep.get("defects") or [],
            "exclusion_reason": ep.get("exclusion_reason"),
            "load_bearing": names in load_bearing,
        })
    rows.sort(key=lambda r: (not r["load_bearing"], r["subject"], r["start"]))
    return rows, load_bearing


def main() -> int:
    ap = argparse.ArgumentParser(
        description=("Render the human review sheet for relationship claims. "
                     "Read-only; spends no quota."))
    ap.add_argument("--episodes", default="data/pilot/records/episodes.json")
    ap.add_argument("--out", default="docs/RELATIONSHIP-REVIEW.md")
    args = ap.parse_args()

    episodes = require(REPO, args.episodes)
    joint_path = REPO / "data/pilot/run/joint_with_nearby.json"
    joint = json.loads(joint_path.read_text()) if joint_path.exists() else None

    rows, _ = build(episodes, joint)
    n_lb = sum(1 for r in rows if r["load_bearing"])
    unreferenced = sum(1 for r in rows if not r["has_reference"])

    L = ["# Relationship claims — human review sheet", "",
         "Every relationship in this project is a Wikidata CANDIDATE. The plan "
         "keeps full human review of real-life factual claims, and this is the "
         "sheet for it. Nothing here decides anything: each claim sits beside "
         "what Wikidata actually states, so a person can confirm or reject it.",
         "",
         f"`data_as_of` {episodes.get('data_as_of', 'unknown')}. "
         f"{len(rows)} episodes, of which **{n_lb}** "
         f"{'feeds' if n_lb == 1 else 'feed'} a jointly covered "
         f"pairing and {'carries' if n_lb == 1 else 'carry'} a published gap. "
         f"**{unreferenced}** carry no "
         f"reference on the Wikidata statement at all — those are the ones most "
         f"likely to be wrong, and they are marked.", ""]
    if n_lb:
        L += [f"**Read the first {n_lb} first.** Everything the report says "
              f"about real-life pairings rests on "
              f"{'it' if n_lb == 1 else 'them'}.", ""]

    for r in rows:
        flag = " — **LOAD-BEARING**" if r["load_bearing"] else ""
        L += [f"## {r['subject']} + {r['partner']}{flag}", "",
              # The statement lives on the subject's Wikidata page. The sheet
              # said only whether a reference EXISTS; a reviewer then had to
              # find the page themselves for every one of 31 rows.
              f"- Wikidata: "
              f"[{r['subject']} ({r['subject_qid']})]"
              f"(https://www.wikidata.org/wiki/{r['subject_qid']})"
              f" · [{r['partner']} ({r['partner_qid']})]"
              f"(https://www.wikidata.org/wiki/{r['partner_qid']})",
              f"- stages: {', '.join(r['stages'])}",
              f"- start: {r['start']}   end: {r['end']}",
              f"- Wikidata reference on the statement: "
              f"**{'yes' if r['has_reference'] else 'NO — check this one'}**",
              f"- scorable: {r['scorable']}"
              + (f"   excluded: {r['exclusion_reason']}"
                 if r['exclusion_reason'] else ""),
              ]
        if r["defects"]:
            # Defects are dicts ({kind, detail}), not strings. Joining them
            # raised rather than printing "{'kind': ...}", which is the right
            # way round for a sheet a person will act on.
            L += ["- defects: " + "; ".join(
                f"{d['kind']} ({d['detail']})" if isinstance(d, dict) else str(d)
                for d in r["defects"])]
        L += ["",
              "**Did this relationship happen, over these dates?**  "
              "[ ] yes  [ ] no  [ ] dates wrong — notes:", "", "---", ""]

    out = REPO / args.out
    out.write_text("\n".join(L) + "\n")
    print(f"{len(rows)} episodes, {n_lb} load-bearing, "
          f"{unreferenced} without a Wikidata reference")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
