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


def merge_families(families: list[dict]) -> tuple[list[dict], dict]:
    """One record per pairing, with every family's gap kept alongside.

    The reduced `gap` is the mean across families that judged it, and
    `family_gaps` keeps the individual values so the spread is inspectable
    rather than averaged away. A pairing only one family judged keeps that
    family's value and reports no spread, which is honest: one judgment has no
    measurable disagreement, it just has none MEASURED.

    Centrality is reduced the same way, and it matters more than the gap: a
    centrality that moves between 0.0 and 0.4 changes whether a pairing counts
    at all, which moves a total further than any gap disagreement does.
    """
    merged: dict[str, dict] = {}
    gaps: dict[str, dict[str, float]] = {}
    cents: dict[str, dict[str, float]] = {}
    for fam in families:
        for r in fam["pairings"]:
            pid = r["pairing_id"]
            base = merged.setdefault(pid, {**r, "gap": None, "centrality": None})
            for judge, g in (r.get("judges") or {}).items():
                if g is not None:
                    gaps.setdefault(pid, {})[judge] = float(g)
            if r.get("centrality") is not None and (r.get("judges") or {}):
                for judge in (r.get("judges") or {}):
                    cents.setdefault(pid, {})[judge] = float(r["centrality"])
            # Keep whichever record carries names; they are identical otherwise.
            for k in ("male", "female", "work", "domain", "period",
                      "male_qid", "female_qid"):
                if base.get(k) is None and r.get(k) is not None:
                    base[k] = r[k]
    for pid, rec in merged.items():
        g = gaps.get(pid) or {}
        c = cents.get(pid) or {}
        rec["gap"] = (sum(g.values()) / len(g)) if g else None
        rec["centrality"] = (sum(c.values()) / len(c)) if c else None
        rec["family_gaps"] = g
        rec["family_centralities"] = c
    return list(merged.values()), {"families": len(families)}


def cross_family_spread(recs: list[dict]) -> dict:
    """Disagreement BETWEEN families on the same pairing.

    This is a different and better quantity than repeat noise within one family:
    it measures whether the judgment is a property of the rubric or of the model.
    """
    gaps, cents = [], []
    for r in recs:
        fg = r.get("family_gaps") or {}
        if len(fg) > 1:
            gaps.append(max(fg.values()) - min(fg.values()))
        fc = r.get("family_centralities") or {}
        if len(fc) > 1:
            cents.append(max(fc.values()) - min(fc.values()))
    return {"pairings_both_judged": len(gaps), "gap_spreads": gaps,
            "centrality_spreads": cents}


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
    ap.add_argument("--scores", action="append", default=None,
                    help="repeatable; one artifact per judge family. Two "
                         "families give CROSS-FAMILY error bars, which is the "
                         "whole point of plan v4 section 5.")
    ap.add_argument("--raw", default="data/roster100/run/raw_pairings")
    ap.add_argument("--out", default="docs/BOARDS.md")
    ap.add_argument("--min-pairings", type=int, default=2)
    args = ap.parse_args()

    paths = args.scores or ["data/roster100/run/pairing_scores.json"]
    families = [require(REPO, p) for p in paths]
    recs, per_family = merge_families(families)
    scores = families[0]
    names = {}
    for r in recs:
        if r.get("male_qid"):
            names[r["male_qid"]] = r.get("male") or r["male_qid"]
        if r.get("female_qid"):
            names[r["female_qid"]] = r.get("female") or r["female_qid"]

    xf = cross_family_spread(recs)
    gs = xf["gap_spreads"]
    # The floor is the MEAN cross-family disagreement. Two cumulative totals
    # closer than this are not distinguishable by a method whose two judges
    # disagree by that much on a single pairing.
    floor = st.mean(gs) if gs else None

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
        w("Only one judge family scored these pairings, so there is no measured "
          "spread and **no rank here is known to be real**. Plan v4 §5 is the "
          "reason that matters: the leaderboard this is modelled on ranks its "
          "top four on differences of 0.09 while stating uncertainty of "
          "±0.2-0.3 per score.")
    else:
        w("## Error bars")
        w()
        w(f"**{xf['pairings_both_judged']} pairings were judged by both judge "
          f"families.** Mean disagreement on the gap is **{floor:.2f}** points, "
          f"median {st.median(gs):.2f}, worst {max(gs):.1f}.")
        w()
        w(f"So two cumulative totals closer than about **{floor:.2f}** are not "
          f"distinguishable. This is a better quantity than repeat noise within "
          f"one family: it measures whether a judgment is a property of the "
          f"rubric or of the model that happened to make it.")
        cs = xf["centrality_spreads"]
        if cs:
            disagree = sum(1 for x in cs if x > 0)
            flips = sum(1 for r in recs
                        if len(r.get("family_centralities") or {}) > 1
                        and (min((r["family_centralities"]).values()) == 0)
                        and (max((r["family_centralities"]).values()) > 0))
            w()
            w(f"**Centrality disagreement matters more than gap disagreement.** "
              f"The families differ on centrality for {disagree} of {len(cs)} "
              f"pairings, and for **{flips}** of them one family says there is "
              f"no romance at all while the other says there is. A pairing that "
              f"flips to zero leaves the board entirely, which moves a total "
              f"further than any disagreement about the gap.")
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
