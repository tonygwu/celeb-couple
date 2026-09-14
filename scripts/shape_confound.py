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
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402


#: DESCRIPTIVE statistics use `statistics.pstdev`, deliberately, and that is
#: not an oversight to be harmonised with `measure_rater_noise.py`, which uses
#: the sample SD. The difference is what the number is FOR:
#:
#:   - Here the question is "how spread out are the estimates this corpus
#:     holds", and the corpus is the whole of what is being described. The
#:     population formula answers exactly that.
#:   - There the question is "what is the standard deviation of the rating
#:     PROCESS", inferred from four repeat draws that are a sample of it. The
#:     population formula underestimates that by 13% at n = 4, which understated
#:     the published noise floor.
#:
#: Same function name, two different questions, two different right answers.


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/pilot/run/shape_confound.json")
    args = ap.parse_args()

    obs = require(REPO, "data/pilot/observations/observations.json")
    scores = require(REPO, "data/pilot/run/evidenced_scores.json")
    joint = require(REPO, "data/pilot/run/joint_with_nearby.json")

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
    # eta-squared is biased UPWARD, and the bias grows with the number of
    # groups and shrinks with n. This corpus has 39 estimates across 5 shape
    # groups, two of which hold a single estimate -- and a group of one has its
    # mean equal to its value by construction, so it contributes to
    # between-group variance with no within-group variance to offset it.
    #
    # Measured here: eta^2 0.389 against omega^2 0.311. The published 39% was
    # roughly eight percentage points high. omega-squared is the standard
    # unbiased estimator and is what the documents now lead with.
    k = len(by_shape)
    n_all = len(all_vals)
    ms_within = ((ss_total - ss_between) / (n_all - k)) if n_all > k else None
    omega_sq = (
        (ss_between - (k - 1) * ms_within) / (ss_total + ms_within)
        if ms_within is not None and (ss_total + ms_within) else None)

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
        # omega is the headline: eta is kept because earlier documents quote it
        # and because the pair together shows how much of the figure was bias.
        "omega_squared_shape_explains": (
            None if omega_sq is None else round(omega_sq, 3)),
        "eta_squared_shape_explains_biased": (
            None if eta_sq is None else round(eta_sq, 3)),
        "eta_squared_shape_explains": None if eta_sq is None else round(eta_sq, 3),
        "effect_size_note": (
            "omega-squared is the unbiased estimator and is the figure to "
            "quote. eta-squared is biased upward, and with 5 shape groups over "
            f"{n_all} estimates -- two groups holding a single estimate -- the "
            "gap between them is the size of that bias."),
        "groups": {kk: len(vv) for kk, vv in sorted(by_shape.items())},
        "jointly_covered_pairings": len(joint.get("jointly_covered", [])),
        "pairings_with_mismatched_shapes": len(mismatched),
        "mismatched": mismatched,
        "reading": (
            "Evidence type explains "
            f"{round((omega_sq or 0) * 100)}% of the variance in the estimates "
            f"(omega-squared, unbiased; the biased eta-squared reads "
            f"{round((eta_sq or 0) * 100)}%). "
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
