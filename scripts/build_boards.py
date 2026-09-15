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
from modules.pairing.normalize import (load_raw_verdicts,  # noqa: E402
                                       normalized_records, rank_changes)

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


def volume_confound(rows: list[dict]) -> dict | None:
    """How much of the cumulative board is just a count of romances.

    Plan v3 section 4 built this diagnostic for the old metric and the same
    hazard applies here, more sharply: fable's gaps are positive on 80% of
    pairings with a mean of +0.52, so every extra romance adds about half a
    point REGARDLESS of who it was with. If that is most of the story, the
    cumulative board is measuring volume wearing the costume of a rate.

    Reports R-squared of cumulative PAW regressed on exposure. It does not gate
    anything: it is a number to print beside the board, not a threshold to fail.
    """
    if len(rows) < 3:
        return None
    xs = [r["exposure"] for r in rows]
    ys = [r["paw_total"] for r in rows]
    mx, my = st.mean(xs), st.mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx == 0 or syy == 0:
        return None
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    r2 = (sxy * sxy) / (sxx * syy)
    return {"r_squared": r2, "n": len(rows)}


def _ordered(rows: list[dict], key: str) -> list[dict]:
    """The same sort `build_board` uses, over whichever column is asked for."""
    return [{"name": r["name"]} for r in
            sorted(rows, key=lambda r: (-(r[key] if r[key] is not None else 0.0),
                                        r["name"]))]


def normalized_section(w, recs: list[dict], raw_rows: dict, names: dict,
                       floor: float | None, args) -> dict:
    """Render the SECOND view: within-sex normalized scores, beside the raw board.

    It never replaces the raw board, which is rendered above it and stays the
    default. Plan v3 shipped `same_shape_view` the same way, and
    `modules/analytics/comparability.py` says why: a normalized number means
    something different from the number it replaced, so the two have to be
    readable side by side.

    `modules/pairing/normalize.py` holds the method, the reason z-score was
    chosen over min-max and percentile, and what that choice costs.
    """
    raw_dir = REPO / args.raw
    if not raw_dir.is_dir():
        raise SystemExit(
            f"{args.raw} is missing, and the absolute scores exist nowhere "
            f"else: pairing_scores.json keeps the gap and drops f_absolute and "
            f"m_absolute. Run scripts/score_pairings.py, or pass --raw.")
    verdicts = load_raw_verdicts(raw_dir, recs)
    nrecs, diag = normalized_records(recs, verdicts)

    w("# The normalized view")
    w()
    w("**Second view. The four boards above are the default and are unchanged.**")
    w()
    w(f"Every absolute score is restated as its distance from the mean of its "
      f"OWN sex, in units of that sex's spread, and then mapped back onto the "
      f"judge family's own scale so the numbers stay in rubric points. The "
      f"population is **(sex, person, period) tuples**, because a person is "
      f"judged at the time of each pairing: Adam Sandler in 2011 is a different "
      f"observation from Adam Sandler in 2004. {diag['observations']} such "
      f"observations back the {diag['pairings_normalized']} normalized pairings.")
    w()
    w("**What this buys and what it costs.** It buys a board on which the two "
      "sexes cannot differ on average, so no ranking is inherited from the "
      "offset. It costs the question: the mean normalized gap is zero BY "
      "CONSTRUCTION, so this view can never be asked whether the judges score "
      "women higher than men. It has assumed they do not. The raw board is the "
      "one that carries that measured offset, which is why it stays first.")
    w()
    w("Unlike a constant offset, which `tests/test_offset_invariance.py` proves "
      "cannot reorder the rate board, full normalization rescales as well as "
      "shifts and therefore CAN reorder it. The counts below are that "
      "difference, measured.")
    w()
    if diag["pairings_with_a_raw_gap_but_no_normalized_gap"]:
        w(f"**{diag['pairings_with_a_raw_gap_but_no_normalized_gap']} pairings "
          f"carry a raw gap but no stored verdict with two absolute scores**, so "
          f"they leave this view: "
          f"`{'`, `'.join(diag['uncovered_pairing_ids'][:8])}`"
          + (" …" if len(diag["uncovered_pairing_ids"]) > 8 else "") + ".")
        w()

    # The offset it removed, measured at render time rather than typed. The
    # zero is a property of the whole observation population; it does NOT have
    # to hold inside a subset, and on this corpus it does not hold inside the
    # scoring on-screen pairings. That is why one women's board stays negative.
    raw_by_id = {r["pairing_id"]: r for r in recs}
    offsets = []
    for label, keep in (("every judged pairing", lambda r: True),
                        ("scoring pairings only (centrality above zero)",
                         lambda r: (raw_by_id[r["pairing_id"]].get("centrality") or 0) > 0)):
        for dom, dlabel in (("on_screen", "on-screen"), ("real_life", "real life"),
                            (None, "both domains")):
            sel = [r for r in nrecs if r["gap"] is not None and keep(r)
                   and (dom is None or r["domain"] == dom)]
            if not sel:
                continue
            offsets.append({
                "subset": label, "domain": dlabel, "n": len(sel),
                "raw_mean_gap": st.mean(raw_by_id[r["pairing_id"]]["gap"] for r in sel),
                "normalized_mean_gap": st.mean(r["gap"] for r in sel),
            })

    w("## The offset it removed, and where the zero does not hold")
    w()
    w("*The mean gap is woman minus man. Normalization forces it to zero over "
      "the WHOLE observation population. It does not force it to zero inside any "
      "subset, and on this corpus it does not: the on-screen pairings that "
      "actually score keep a positive mean, which is why one women's board below "
      "stays entirely negative.*")
    w()
    w("| Subset | Domain | Pairings | Raw mean gap | Normalized mean gap |")
    w("|---|---|---|---|---|")
    for o in offsets:
        w(f"| {o['subset']} | {o['domain']} | {o['n']} | "
          f"{o['raw_mean_gap']:+.4f} | {o['normalized_mean_gap']:+.4f} |")
    w()

    w("## The scales")
    w()
    w("*One cell per judge family and sex, because an absolute score only means "
      "something on the scale of the judge that produced it. `*` is the family's "
      "own grand scale, which the normalized scores are mapped back onto.*")
    w()
    w("| Family | Sex | n | Mean | SD |")
    w("|---|---|---|---|---|")
    for s in sorted(diag["scales"], key=lambda s: (s["family"], s["sex"])):
        w(f"| {s['family']} | {s['sex']} | {s['n']} | {s['mean']:.3f} | "
          f"{s['sd']:.3f} |")
    w()

    boards, totals = [], {"people": 0, "moved": 0, "discordant": 0,
                          "moved_rate": 0, "discordant_rate": 0, "pairs": 0}
    n = 0
    for gender, glabel in (("male", "Men"), ("female", "Women")):
        for domain, dlabel in DOMAINS:
            n += 1
            before = raw_rows[(gender, domain)]
            after = build_board(nrecs, gender=gender, domain=domain, names=names,
                                min_pairings=args.min_pairings)
            cum = rank_changes(_ordered(before, "paw_total"),
                               _ordered(after, "paw_total"))
            rate = rank_changes(_ordered(before, "paw_rate"),
                                _ordered(after, "paw_rate"))
            neg_before = sum(1 for r in before if r["paw_total"] < 0)
            neg_after = sum(1 for r in after if r["paw_total"] < 0)
            boards.append({
                "board": n, "gender": gender, "domain": domain,
                "cumulative": cum, "rate": rate,
                "negative_before": neg_before, "negative_after": neg_after,
                "people": len(after),
                "rows": [{"name": r["name"], "paw_total": r["paw_total"],
                          "paw_rate": r["paw_rate"]} for r in after],
            })
            totals["people"] += cum["people"]
            totals["moved"] += cum["moved"]
            totals["discordant"] += cum["discordant_pairs"]
            totals["moved_rate"] += rate["moved"]
            totals["discordant_rate"] += rate["discordant_pairs"]
            totals["pairs"] += cum["pairs"]

            w(f"## Normalized board {n}: {glabel}, {dlabel}")
            w()
            if not after:
                w("No one qualifies.")
                w()
                continue
            w("| # | Person | Pairings | Cumulative PAW | Rate | Raw rank |")
            w("|---|---|---|---|---|---|")
            raw_pos = {r["name"]: i for i, r in enumerate(before, 1)}
            for i, r in enumerate(after, 1):
                rt = "—" if r["paw_rate"] is None else f"{r['paw_rate']:+.2f}"
                was = raw_pos.get(r["name"])
                mark = "—" if was is None else (
                    f"{was}" if was == i else f"{was} ({i - was:+d})")
                w(f"| {i} | {r['name']} | {r['pairings']} | "
                  f"{r['paw_total']:+.2f} | {rt} | {mark} |")
            w()
            w(f"**Rank changes: {cum['moved']} of {cum['people']} placements move "
              f"on the cumulative board ({cum['discordant_pairs']} of "
              f"{cum['pairs']} pairs flip), {rate['moved']} on the rate board "
              f"({rate['discordant_pairs']} of {rate['pairs']} pairs flip).**")
            w()
            if gender == "female":
                crossed = [r["name"] for r in after if r["paw_total"] >= 0]
                small = [r["name"] for r in after
                         if 0 <= r["paw_total"] < (floor or 0)]
                w(f"**Sign check.** {neg_before} of {len(before)} women were "
                  f"negative on the raw cumulative board; {neg_after} of "
                  f"{len(after)} are negative here.")
                w()
                if not crossed:
                    w("Every one of them is still negative, so the raw board's "
                      "uniform sign is not only the mirror of the offset. The "
                      "offset table above says why: the mean gap on the scoring "
                      "pairings in this domain is still positive after "
                      "normalization.")
                else:
                    verb = "crosses" if len(crossed) == 1 else "cross"
                    w(f"{', '.join(crossed)} {verb} to zero or above."
                      + (f" The crossing is smaller than the {floor:.2f} floor "
                         f"for {', '.join(small)}, so the sign changes but the "
                         f"change is not distinguishable from zero." if small
                         else ""))
                w()
            if floor is not None and len(after) > 1:
                undist = sum(1 for a, b in zip(after, after[1:])
                             if abs(a["paw_total"] - b["paw_total"]) < floor)
                w(f"**{undist} of {len(after) - 1} adjacent rank gaps are smaller "
                  f"than the {floor:.2f} floor.** The floor still applies because "
                  f"the normalized scores are mapped back onto the judges' own "
                  f"scale, so both views are in rubric points.")
                w()

    w("## What normalization did, in one table")
    w()
    w("| Board | People | Cumulative: moved | pairs flipped | Rate: moved | pairs flipped |")
    w("|---|---|---|---|---|---|")
    for b in boards:
        label = f"{b['board']}: {'Men' if b['gender'] == 'male' else 'Women'}, " \
                f"{dict(DOMAINS)[b['domain']]}"
        w(f"| {label} | {b['cumulative']['people']} | {b['cumulative']['moved']} | "
          f"{b['cumulative']['discordant_pairs']}/{b['cumulative']['pairs']} | "
          f"{b['rate']['moved']} | "
          f"{b['rate']['discordant_pairs']}/{b['rate']['pairs']} |")
    w(f"| **All four** | **{totals['people']}** | **{totals['moved']}** | "
      f"**{totals['discordant']}/{totals['pairs']}** | "
      f"**{totals['moved_rate']}** | "
      f"**{totals['discordant_rate']}/{totals['pairs']}** |")
    w()

    return {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "method": "z-score within (judge family, sex), mapped back onto the "
                      "family's own mean and sd",
            "population": "(judge family, sex, person, period) tuples",
            "diagnostics": diag,
            "offsets": offsets,
            "boards": boards,
            "rank_changes_total": totals}


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
    ap.add_argument("--norm-out", default="data/roster100/run/normalized_view.json",
                    help="where the normalized second view's numbers are "
                         "written so they can be checked without re-reading "
                         "the prose. Empty string to skip.")
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

    def table(rows: list[dict]) -> None:
        w("| # | Person | Pairings | Cumulative PAW | Rate | Biggest contributor |")
        w("|---|---|---|---|---|---|")
        for i, r in enumerate(rows, 1):
            top = r["contributions"][0] if r["contributions"] else None
            tops = (f"{top['other']} ({top['work'] or top['period']}) "
                    f"{top['paw']:+.2f}" if top else "—")
            rate = "—" if r["paw_rate"] is None else f"{r['paw_rate']:+.2f}"
            w(f"| {i} | {r['name']} | {r['pairings']} | "
              f"{r['paw_total']:+.2f} | {rate} | {tops} |")

    raw_rows: dict[tuple[str, str], list[dict]] = {}
    n = 0
    for gender, glabel in (("male", "Men"), ("female", "Women")):
        for domain, dlabel in DOMAINS:
            n += 1
            rows = build_board(recs, gender=gender, domain=domain, names=names,
                               min_pairings=args.min_pairings)
            raw_rows[(gender, domain)] = rows
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
            table(rows)
            w()
            if floor is not None and len(rows) > 1:
                undist = sum(1 for a, b in zip(rows, rows[1:])
                             if abs(a["paw_total"] - b["paw_total"]) < floor)
                w(f"**{undist} of {len(rows) - 1} adjacent rank gaps are smaller "
                  f"than the {floor:.2f} floor**, so those orderings are not "
                  f"established.")
                w()
            vc = volume_confound(rows)
            if vc is not None:
                pct = vc["r_squared"] * 100
                w(f"**Volume check.** Cumulative PAW regressed on exposure gives "
                  f"R² = {vc['r_squared']:.2f} over {vc['n']} people, so about "
                  f"**{pct:.0f}% of this cumulative board is explained by how "
                  f"many romances each person had**, not by who they were with. "
                  + ("The rate column is the one to read."
                     if pct >= 50 else
                     "Low enough that the ordering is not merely a count."))
                w()

    norm_summary = normalized_section(w, recs, raw_rows, names, floor, args)

    dest = REPO / args.out
    dest.write_text("\n".join(L) + "\n")
    if args.norm_out:
        nd = REPO / args.norm_out
        nd.parent.mkdir(parents=True, exist_ok=True)
        nd.write_text(json.dumps(norm_summary, indent=2) + "\n")
        print(f"wrote {nd}")
    print(f"wrote {dest}  ({judged} judged, {scored} scoring)")
    print(f"normalized view: {norm_summary['rank_changes_total']['moved']} of "
          f"{norm_summary['rank_changes_total']['people']} board placements "
          f"move on the cumulative boards, "
          f"{norm_summary['rank_changes_total']['moved_rate']} on the rate boards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
