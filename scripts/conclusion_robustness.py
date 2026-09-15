#!/usr/bin/env python3
"""Do the capstone's conclusions survive different methodological choices?

`docs/THE-TRAP.md` rests on choices that were made for good reasons and could
defensibly have been made otherwise: the +/-1 nearby-period bound, the romance
filter on co-starring films, and enforcing shape comparability rather than
labelling it. Each was argued in the plan. None was tested for whether the
conclusion depends on it.

A conclusion that only holds at one setting of three dials is a property of the
dials. This re-derives the two structural claims at every setting and reports
where they hold.

It changes no artifact and recommends nothing. Read-only, and it spends no
model quota -- every setting reuses the same estimates.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402
from modules.consensus.nearby import resolve_period  # noqa: E402


def evaluate(obs, scores, eps, films, romance, *, bound: int,
             romance_filter: bool, floor: float | None = None) -> dict:
    """Joint coverage and comparability at one setting of the dials."""
    shape_of: dict[tuple[str, str], set[str]] = {}
    for o in obs["observations"]:
        shape_of.setdefault((o["person_id"], o["concerns_period"]), set()).add(
            o["evidence_type"])

    est: dict[str, dict[str, float]] = {}
    for r in scores["person_periods"]:
        if r["estimate"] is not None:
            est.setdefault(r["person_id"], {})[r["period"]] = r["estimate"]

    qualifying = None
    if romance_filter and romance:
        qualifying = {(c["work_qid"], c["male_qid"], c["female_qid"])
                      for c in romance["candidates"] if c.get("qualifies")}

    rows = []

    def _add(a, b, period, label):
        ra = resolve_period(period, est.get(a, {}), bound)
        rb = resolve_period(period, est.get(b, {}), bound)
        if not (ra.scored and rb.scored):
            return
        sa = "+".join(sorted(shape_of.get((a, ra.source_period), [])))
        sb = "+".join(sorted(shape_of.get((b, rb.source_period), [])))
        rows.append({
            "label": label, "period": period,
            "gap": round(est[a][ra.source_period] - est[b][rb.source_period], 3),
            "comparable": bool(sa and sb and sa == sb),
        })

    for c in films["candidates"]:
        y = c["release"][:4]
        if not y.isdigit():
            continue
        if qualifying is not None and (c["work_qid"], c["male_qid"],
                                       c["female_qid"]) not in qualifying:
            continue
        _add(c["male_qid"], c["female_qid"], y, c["title"])

    for e in eps["episodes"]:
        for y in [str(v) for v in e.get("adult_years") or []]:
            _add(e["subject_qid"], e["partner_qid"], y, "relationship")

    # DETECTABLE, not merely non-zero. `gap != 0.0` was written when one judge
    # family scored the corpus and returned integers. The mean-of-two reducer
    # produces half-integers, so a 0.5 gap -- one judge saying 93 where the
    # other said 92, both inside band 90-100 -- counted as a comparable pairing
    # with a real difference and broke the capstone claim. It is an order of
    # magnitude under the measured floor.
    #
    # With no measured floor the counts fall back to `!= 0`, and the artifact
    # says so in `floor_used` rather than letting a reader assume one was
    # applied.
    def detectable(r) -> bool:
        return abs(r["gap"]) > floor if floor is not None else r["gap"] != 0.0

    comparable = [r for r in rows if r["comparable"]]
    nonzero_comparable = [r for r in comparable if detectable(r)]
    nonzero_any = [r for r in rows if detectable(r)]
    return {
        "bound": bound, "romance_filter": romance_filter,
        "floor_used": floor,
        "jointly_covered": len(rows),
        "comparable": len(comparable),
        "comparable_with_a_nonzero_gap": len(nonzero_comparable),
        "nonzero_gaps_that_are_shape_mismatched": sum(
            1 for r in nonzero_any if not r["comparable"]),
        "nonzero_gaps_total": len(nonzero_any),
        "examples": [f"{r['label']} {r['period']}: {r['gap']:+g}"
                     for r in nonzero_comparable][:4],
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=("Re-derive the capstone's structural claims under "
                     "alternative methodological choices. Read-only; spends no "
                     "quota."))
    ap.add_argument("--max-bound", type=int, default=4)
    ap.add_argument("--out", default="data/pilot/run/conclusion_robustness.json")
    args = ap.parse_args()

    obs = require(REPO, "data/pilot/observations/observations.json")
    scores = require(REPO, "data/pilot/run/evidenced_scores.json")
    eps = require(REPO, "data/pilot/records/episodes.json")
    films = require(REPO, "data/pilot/records/onscreen_candidates.json")
    noise = require(REPO, "data/pilot/run/rater_noise.json")
    _by_shape = (noise.get("headline") or {}).get("by_shape") or {}
    _floors = [v["least_significant_difference_95pct"] for v in _by_shape.values()
               if v.get("least_significant_difference_95pct") is not None]
    floor = max(_floors) if _floors else None
    romance_path = REPO / "data/pilot/records/romance.json"
    romance = json.loads(romance_path.read_text()) if romance_path.exists() else None

    settings = [evaluate(obs, scores, eps, films, romance,
                         bound=b, romance_filter=rf, floor=floor)
                for b in range(0, args.max_bound + 1)
                for rf in (True, False)]

    broken = [s for s in settings if s["comparable_with_a_nonzero_gap"]]
    mixed = [s for s in settings
             if s["nonzero_gaps_total"]
             and s["nonzero_gaps_that_are_shape_mismatched"] < s["nonzero_gaps_total"]]

    payload = {
        "settings": settings,
        "claim_every_comparable_gap_is_zero": {
            "holds_at": [f"bound {s['bound']}, romance_filter {s['romance_filter']}"
                         for s in settings if not s["comparable_with_a_nonzero_gap"]],
            "fails_at": [f"bound {s['bound']}, romance_filter {s['romance_filter']}"
                         for s in broken],
        },
        "claim_every_nonzero_gap_is_shape_mismatched": {
            "fails_at": [f"bound {s['bound']}, romance_filter {s['romance_filter']}"
                         for s in mixed],
        },
        "reading": None,
        "caveat": (
            "Every setting reuses the SAME estimates. This tests whether the "
            "conclusions depend on the three methodological dials, not whether "
            "they survive different evidence."),
    }
    payload["reading"] = (
        f"Across {len(settings)} settings of the nearby-period bound and the "
        f"romance filter, the claim that every shape-comparable pairing has a "
        f"gap of exactly zero fails at {len(broken)} of them"
        + (f" ({', '.join(payload['claim_every_comparable_gap_is_zero']['fails_at'])})"
           if broken else "")
        + f", and the claim that every non-zero gap is shape-mismatched fails "
          f"at {len(mixed)}.")

    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2) + "\n")

    print(f"{'bound':>6} {'romance':>8} {'joint':>6} {'comp':>5} "
          f"{'comp!=0':>8} {'nonzero':>8} {'mismatched':>11}")
    for s in settings:
        print(f"{s['bound']:>6} {str(s['romance_filter']):>8} "
              f"{s['jointly_covered']:>6} {s['comparable']:>5} "
              f"{s['comparable_with_a_nonzero_gap']:>8} "
              f"{s['nonzero_gaps_total']:>8} "
              f"{s['nonzero_gaps_that_are_shape_mismatched']:>11}")
    print()
    print(payload["reading"])
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
