#!/usr/bin/env python3
"""Does the SHAPE of a person's evidence determine their estimate?

THE WORRY
---------
The first real pairing gaps this project produced pair award-shaped evidence
against inclusion-shaped evidence. Brad Pitt is judged by a Sexiest Man Alive
win and lands at 92; Jennifer Aniston by list inclusions and lands at 80. The
resulting -12 gap could be a fact about how they were perceived, or it could be
an artifact of which publication happened to cover each of them and in what
format.

If evidence type alone predicts the estimate, then any pairing whose two sides
carry different evidence types has a gap manufactured by the sources. That is
the most serious systematic bias available to this design, and it has to be
measured rather than hoped away.

Read-only. Spends no model quota.
"""
from __future__ import annotations
import argparse, json, statistics, sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/pilot/run/shape_confound.json")
    args = ap.parse_args()

    obs = json.loads((REPO / "data/pilot/observations/observations.json").read_text())
    scores = json.loads((REPO / "data/pilot/run/evidenced_scores.json").read_text())
    joint = json.loads((REPO / "data/pilot/run/joint_with_nearby.json").read_text())

    shape_of: dict[tuple[str, str], set[str]] = defaultdict(set)
    for o in obs["observations"]:
        shape_of[(o["person_id"], o["concerns_period"])].add(o["evidence_type"])

    by_shape: dict[str, list[float]] = defaultdict(list)
    rows = []
    for r in scores["person_periods"]:
        if r["estimate"] is None:
            continue
        shapes = sorted(shape_of.get((r["person_id"], r["period"]), []))
        key = "+".join(shapes) if shapes else "unknown"
        by_shape[key].append(r["estimate"])
        rows.append({"person": r["person"], "period": r["period"],
                     "estimate": r["estimate"], "shape": key})

    summary = {}
    for k, v in sorted(by_shape.items()):
        summary[k] = {"n": len(v), "mean": round(statistics.mean(v), 2),
                      "min": min(v), "max": max(v),
                      "sd": round(statistics.pstdev(v), 3) if len(v) > 1 else 0.0}

    # How much of the total variance does shape alone explain?
    all_vals = [r["estimate"] for r in rows]
    grand = statistics.mean(all_vals) if all_vals else 0.0
    ss_total = sum((v - grand) ** 2 for v in all_vals)
    ss_between = sum(
        len(v) * (statistics.mean(v) - grand) ** 2 for v in by_shape.values())
    eta_sq = (ss_between / ss_total) if ss_total else None

    mismatched = []
    for j in joint.get("jointly_covered", []):
        a = "+".join(sorted(shape_of.get((j["a_qid"], j["a_src"]), [])))
        b = "+".join(sorted(shape_of.get((j["b_qid"], j["b_src"]), [])))
        if a and b and a != b:
            mismatched.append({"pairing": j.get("work") or "relationship",
                               "period": j["period"], "a": j["a"], "a_shape": a,
                               "b": j["b"], "b_shape": b})

    payload = {
        "by_shape": summary,
        "eta_squared_shape_explains": None if eta_sq is None else round(eta_sq, 3),
        "jointly_covered_pairings": len(joint.get("jointly_covered", [])),
        "pairings_with_mismatched_shapes": len(mismatched),
        "mismatched": mismatched,
        "reading": (
            "Evidence type explains "
            f"{round((eta_sq or 0) * 100)}% of the variance in the estimates. "
            "Where a pairing's two sides carry DIFFERENT evidence types, the "
            "signed gap is substantially a statement about which publication "
            "covered whom in what format, not about the two people. Every such "
            "pairing must carry that caveat on the page."
        ),
        "rows": sorted(rows, key=lambda r: (r["shape"], r["estimate"])),
    }
    (REPO / args.out).write_text(json.dumps(payload, indent=2))

    print("estimate distribution by evidence shape:")
    for k, v in summary.items():
        print(f"  {k:40} n={v['n']:2} mean {v['mean']:6} range {v['min']}-{v['max']} "
              f"sd {v['sd']}")
    print(f"\nshape explains {round((eta_sq or 0)*100)}% of estimate variance "
          f"(eta-squared {payload['eta_squared_shape_explains']})")
    print(f"\njointly covered pairings with MISMATCHED evidence shapes: "
          f"{len(mismatched)} of {payload['jointly_covered_pairings']}")
    for m in mismatched:
        print(f"  {m['pairing'][:28]:28} {m['period']}  {m['a'][:16]:16} [{m['a_shape']}]"
              f"  vs  {m['b'][:16]:16} [{m['b_shape']}]")
    print(f"\nwrote {REPO / args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
