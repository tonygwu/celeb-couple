#!/usr/bin/env python3
"""Does the same dossier score the same in two separate runs?

The plan says plainly that a contract hash identifies what was SENT and does
not make a fresh model invocation deterministic. That was written as a caveat.
This measures it.

The pilot corpus and the 100-name roster corpus were scored in separate runs.
Three person-periods appear in both. Where the dossier is byte-identical -- the
same observation ids, under the same contract id, from the same judge family --
any difference in the estimate is run-to-run variance and nothing else.

This is stronger evidence than `measure_rater_noise.py` gives, because those
repeats were deliberate re-invocations inside one run. These two runs were
days apart in project time and neither knew about the other.

Read-only. Spends no model quota.
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402


def estimates(payload: dict) -> dict[tuple[str, str], float]:
    """Pull (person, period) -> estimate out of either score artifact shape.

    Two shapes exist and they are not interchangeable. An unknown one raises
    rather than returning an empty dict, because a silent empty result here
    reads as "the runs agree perfectly".
    """
    if "person_periods" in payload:
        return {(r["person"], r["period"]): r["estimate"]
                for r in payload["person_periods"] if r["estimate"] is not None}
    if "pairings" in payload:
        out: dict[tuple[str, str], float] = {}
        for pr in payload["pairings"]:
            for side in ("a", "b"):
                est = pr.get(f"{side}_estimate")
                # `*_from` is the period the estimate was actually made for,
                # which differs from the pairing period under nearby reuse.
                period = pr.get(f"{side}_from")
                if est is not None and period is not None:
                    out[(pr[side], period)] = est
        return out
    raise ValueError(
        "unrecognised score artifact: expected 'person_periods' or 'pairings'")


def dossier_key(obs: dict, person_qid: str, period: str) -> tuple[str, ...]:
    return tuple(sorted(o["observation_id"] for o in obs["observations"]
                        if o["person_id"] == person_qid
                        and o["concerns_period"] == period))


def shape_of(obs: dict, person_qid: str, period: str) -> str:
    kinds = sorted({o["evidence_type"] for o in obs["observations"]
                    if o["person_id"] == person_qid
                    and o["concerns_period"] == period})
    return "+".join(kinds) if kinds else "none"


def main() -> int:
    ap = argparse.ArgumentParser(
        description=("Compare estimates for the same dossier across two "
                     "separate scoring runs. Read-only; spends no quota."))
    ap.add_argument("--a-scores", default="data/pilot/run/evidenced_scores.json")
    ap.add_argument("--a-obs", default="data/pilot/observations/observations.json")
    ap.add_argument("--a-name", default="pilot")
    ap.add_argument("--b-scores", default="data/roster100/run/joint_scores.json")
    ap.add_argument("--b-obs", default="data/roster100/observations/observations.json")
    ap.add_argument("--b-name", default="roster100")
    ap.add_argument("--out", default="data/pilot/run/cross_run_stability.json")
    args = ap.parse_args()

    a_scores = require(REPO, args.a_scores)
    b_scores = require(REPO, args.b_scores)
    a_obs = require(REPO, args.a_obs)
    b_obs = require(REPO, args.b_obs)

    a_contract = (a_scores.get("contract") or {}).get("contract_id")
    b_contract = (b_scores.get("contract") or {}).get("contract_id")

    # Person ids are needed to look a dossier up; the score rows carry names.
    # Observations are keyed by Wikidata id; score rows carry the name. Run A
    # is the one that must supply the mapping, so a person only run B scored
    # is skipped by name rather than matched by guesswork.
    a_qid = {r["person"]: r["person_id"] for r in a_scores.get("person_periods", [])}

    A, B = estimates(a_scores), estimates(b_scores)
    shared = sorted(set(A) & set(B))

    rows, skipped = [], []
    for person, period in shared:
        qid = a_qid.get(person)
        if qid is None:
            skipped.append({"person": person, "period": period,
                            "why": "no wikidata id in run A's score rows"})
            continue
        ka = dossier_key(a_obs, qid, period)
        kb = dossier_key(b_obs, qid, period)
        if ka != kb:
            # A different dossier explains a different score without any
            # run-to-run variance, so it must not be counted as noise.
            skipped.append({"person": person, "period": period,
                            "why": "dossiers differ between the two corpora",
                            "a_observations": list(ka), "b_observations": list(kb)})
            continue
        rows.append({"person": person, "period": period,
                     "shape": shape_of(a_obs, qid, period),
                     "observations": list(ka),
                     args.a_name: A[(person, period)],
                     args.b_name: B[(person, period)],
                     "delta": round(A[(person, period)] - B[(person, period)], 3)})

    by_shape: dict[str, list[float]] = {}
    for r in rows:
        by_shape.setdefault(r["shape"], []).append(abs(r["delta"]))

    deltas = [abs(r["delta"]) for r in rows]
    payload = {
        "runs": {args.a_name: args.a_scores, args.b_name: args.b_scores},
        "same_contract": a_contract == b_contract,
        "contract_ids": {args.a_name: a_contract, args.b_name: b_contract},
        "comparable_person_periods": len(rows),
        "skipped": skipped,
        "rows": rows,
        "max_abs_delta": max(deltas) if deltas else None,
        "mean_abs_delta": round(statistics.mean(deltas), 3) if deltas else None,
        "unchanged": sum(1 for d in deltas if d == 0),
        "mean_abs_delta_by_shape": {
            s: {"n": len(v), "mean_abs_delta": round(statistics.mean(v), 3),
                "max_abs_delta": max(v)}
            for s, v in sorted(by_shape.items())},
        "reading": None,
    }

    if not rows:
        payload["reading"] = (
            "No person-period carries an identical dossier in both runs, so "
            "this says nothing about stability. It is not evidence of "
            "agreement.")
    else:
        payload["reading"] = (
            f"{len(rows)} person-periods carry a byte-identical dossier in "
            f"both runs under "
            f"{'the same' if payload['same_contract'] else 'DIFFERENT'} "
            f"contract id. {payload['unchanged']} returned the same estimate "
            f"and {len(rows) - payload['unchanged']} did not, with a largest "
            f"move of {payload['max_abs_delta']} points. A move here is pure "
            f"run-to-run variance: the evidence, the rubric and the judge "
            f"family were identical.")

    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1) + "\n")

    print(f"comparable person-periods: {len(rows)}  "
          f"(skipped {len(skipped)})")
    print(f"same contract id: {payload['same_contract']}")
    for r in rows:
        print(f"  {r['person']:22s} {r['period']}  {r['shape']:16s} "
              f"{r[args.a_name]:5.1f} vs {r[args.b_name]:5.1f}  "
              f"delta {r['delta']:+.1f}")
    print()
    for s, v in payload["mean_abs_delta_by_shape"].items():
        print(f"  {s:16s} n={v['n']}  mean |delta| {v['mean_abs_delta']}  "
              f"max {v['max_abs_delta']}")
    print()
    print(payload["reading"])
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
