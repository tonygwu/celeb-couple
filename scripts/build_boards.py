#!/usr/bin/env python3
"""Render the four leaderboards from judged pairing gaps. Read-only.

Boards 1 and 2 are the men, on-screen and real-life. Boards 3 and 4 are the
women, and they are the SAME numbers mirrored -- not separate research.

Where repeat judgments exist, every rank carries an interval and a stability
figure. A rank without one is not reported as a rank.
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.artifacts import require              # noqa: E402
from modules.pairing.boards import build_board             # noqa: E402

DOMAINS = (("on_screen", "on-screen"), ("real_life", "real life"))


def repeat_spread(raw_dir: Path) -> dict:
    """Per-pairing spread across repeat judgments of the SAME pairing.

    Returns {} when no repeats exist, and the caller must then report no
    intervals rather than inventing one. A leaderboard whose error bars are
    assumed is worse than one that says it has none.
    """
    by_pairing: dict[str, list[float]] = defaultdict(list)
    cent: dict[str, list[float]] = defaultdict(list)
    if not raw_dir.is_dir():
        return {}
    for f in sorted(raw_dir.glob("*.txt")):
        try:
            o = json.loads(f.read_text())
        except (ValueError, OSError):
            continue
        if not o.get("judged") or o.get("gap") is None:
            continue
        by_pairing[o["pairing_id"]].append(float(o["gap"]))
        if o.get("centrality") is not None:
            cent[o["pairing_id"]].append(float(o["centrality"]))
    return {
        "gap_sd": {k: st.stdev(v) for k, v in by_pairing.items() if len(v) > 1},
        "centrality_sd": {k: st.stdev(v) for k, v in cent.items() if len(v) > 1},
        "repeated_pairings": sum(1 for v in by_pairing.values() if len(v) > 1),
        "repeats_per_pairing": max((len(v) for v in by_pairing.values()), default=0),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Render the four boards. Read-only; spends no quota.")
    ap.add_argument("--scores", default="data/roster100/run/pairing_scores.json")
    ap.add_argument("--raw", default="data/roster100/run/raw_pairings")
    ap.add_argument("--out", default="docs/BOARDS.md")
    ap.add_argument("--min-pairings", type=int, default=2)
    args = ap.parse_args()

    scores = require(REPO, args.scores)
    recs = scores["pairings"]
    names = {}
    for r in recs:
        if r.get("male_qid"):
            names[r["male_qid"]] = r.get("male") or r["male_qid"]
        if r.get("female_qid"):
            names[r["female_qid"]] = r.get("female") or r["female_qid"]

    spread = repeat_spread(REPO / args.raw)
    sds = list((spread.get("gap_sd") or {}).values())
    floor = (st.mean(sds) * 2 if sds else None)

    L: list[str] = []
    def w(s: str = "") -> None:
        L.append(s)

    w("# The four boards")
    w()
    w(f"Generated {datetime.now(timezone.utc).date()} from "
      f"`{args.scores}`, contract `{scores['contract']['contract_id']}` "
      f"({scores['contract']['rubric_version']}).")
    w()
    w("**These are subjective model judgments, not measurements.** No source "
      "backs any number here. Plan v4 §9.")
    w()
    judged = sum(1 for r in recs if r.get("gap") is not None)
    scored = sum(1 for r in recs
                 if r.get("gap") is not None and (r.get("centrality") or 0) > 0)
    w(f"{len(recs)} pairings, {judged} judged, **{scored} with a romance to "
      f"score** (centrality above zero). The rest are cast-list co-appearances "
      f"and contribute nothing.")
    w()

    if floor is None:
        w("## No error bars")
        w()
        w("No pairing has been judged more than once, so there is no measured "
          "spread and **no rank here is known to be real**. Run "
          "`scripts/score_pairings.py --tag _r2` and rerun this to get them. "
          "Plan v4 §5 is the reason that matters: the leaderboard this is "
          "modelled on ranks its top four on differences of 0.09 while stating "
          "uncertainty of ±0.2-0.3 per score.")
    else:
        w("## Error bars")
        w()
        w(f"{spread['repeated_pairings']} pairings judged "
          f"{spread['repeats_per_pairing']} times each. Mean within-pairing "
          f"standard deviation of the gap is {st.mean(sds):.3f}, so two "
          f"cumulative totals closer than about **{floor:.2f}** are not "
          f"distinguishable.")
        csd = list((spread.get("centrality_sd") or {}).values())
        if csd:
            w()
            w(f"Centrality is noisier than the gap: mean sd {st.mean(csd):.3f}. "
              f"A centrality that moves between 0.0 and 0.4 changes whether a "
              f"pairing counts **at all**, which moves a total further than any "
              f"gap disagreement does.")
    w()

    n = 0
    for gender, glabel in (("male", "Men"), ("female", "Women")):
        for domain, dlabel in DOMAINS:
            n += 1
            rows = build_board(recs, gender=gender, domain=domain, names=names,
                               min_pairings=args.min_pairings)
            w(f"## Board {n}: {glabel}, {dlabel}")
            w()
            w(f"*How much they punched above their weight. Positive means their "
              f"partners were judged more conventionally attractive than they "
              f"were. Minimum {args.min_pairings} scored pairings.*")
            w()
            if not rows:
                w("No one qualifies. Every pairing in this cell is either "
                  "unjudged or has centrality zero.")
                w()
                continue
            w("| # | Person | Pairings | Cumulative PAW | Rate | Biggest contributor |")
            w("|---|---|---|---|---|---|")
            for i, r in enumerate(rows, 1):
                top = r["contributions"][0] if r["contributions"] else None
                tops = (f"{top['other']} ({top['work'] or top['period']}) "
                        f"{top['paw']:+.2f}" if top else "—")
                rate = "—" if r["paw_rate"] is None else f"{r['paw_rate']:+.2f}"
                w(f"| {i} | {r['name']} | {r['pairings']} | "
                  f"{r['paw_total']:+.2f} | {rate} | {tops} |")
            w()
            if floor is not None and len(rows) > 1:
                undist = sum(1 for a, b in zip(rows, rows[1:])
                             if abs(a["paw_total"] - b["paw_total"]) < floor)
                w(f"**{undist} of {len(rows) - 1} adjacent rank gaps are smaller "
                  f"than the {floor:.2f} floor**, so those orderings are not "
                  f"established.")
                w()

    dest = REPO / args.out
    dest.write_text("\n".join(L) + "\n")
    print(f"wrote {dest}  ({judged} judged, {scored} scoring)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
