#!/usr/bin/env python3
"""Run the measurement stress cases and write a findings report.

These are evaluations, not gates. The script always exits 0 unless it could not
run; a stress finding is a finding, not a build failure.

    .venv/bin/python scripts/run_stress.py --out data/pilot/stress \
        --fable-account /Users/tonygwu/.claude-e --max-astra 10
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.accounts import resolve_account            # noqa: E402
from packages.llmkit.budget import Budget, BudgetExhausted          # noqa: E402
from packages.llmkit.contract import load_contract                   # noqa: E402
from packages.llmkit.judges import ClaudeJudge, CodexJudge           # noqa: E402
from modules.consensus.dossier import build_dossier                  # noqa: E402
from modules.consensus.score import score_dossier                    # noqa: E402
from modules.consensus.stress import CASES, EDITIONS                 # noqa: E402

RUBRIC = REPO / "rubrics/standing/RUBRIC.md"
SCHEMA = REPO / "rubrics/standing/estimate.schema.json"


def main() -> int:
    ap = argparse.ArgumentParser(description='Run the measurement stress cases against the judges. SPENDS MODEL QUOTA.')
    ap.add_argument("--out", required=True)
    ap.add_argument("--fable-account", default=None,
                    help=("Claude Code config dir to run under. No default: "
                          "quota headroom moves between accounts. Run "
                          "`quotapick status` first, or set CELEB_ACCOUNT."))
    ap.add_argument("--fable-model", default="claude-fable-5-1")
    ap.add_argument("--astra-model", default="gpt-6-astra")
    ap.add_argument("--max-fable", type=int, default=25)
    ap.add_argument("--max-astra", type=int, default=10)
    ap.add_argument("--only", default=None, help="run one case id")
    args = ap.parse_args()

    out = Path(args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    contract = load_contract(RUBRIC, SCHEMA, "standing-rubric-2.0")
    rubric_text, schema_text = RUBRIC.read_text(), SCHEMA.read_text()

    fable = ClaudeJudge("fable", args.fable_model, config_dir=resolve_account(args.fable_account))
    astra = CodexJudge("astra", args.astra_model, effort="high")
    budgets = {"fable": Budget(max_calls=args.max_fable),
               "astra": Budget(max_calls=args.max_astra)}

    results: list[dict] = []
    failures: list[dict] = []

    for case in CASES:
        if args.only and case.case_id != args.only:
            continue
        judges = [("fable", fable)] + ([("astra", astra)] if case.cross_family else [])
        for arm, observations in case.arms.items():
            dossier = build_dossier(
                person_id=f"{case.case_id}:{arm}",
                display_name=case.display_names.get(arm, "Jordan Quill"),
                period="2012",
                observations=list(observations),
                editions=EDITIONS,
                anonymise=case.anonymise.get(arm, False),
                shuffle_seed=case.shuffle.get(arm),
            )
            for jname, judge in judges:
                b = budgets[jname]
                try:
                    est, verdicts, fails = score_dossier(
                        dossier, [judge], contract, rubric_text, schema_text,
                        b, out / "raw" / case.case_id,
                        timeout=900,
                    )
                except BudgetExhausted as exc:
                    failures.append({"case": case.case_id, "arm": arm,
                                     "judge": jname, "error_type": "budget_cap_reached",
                                     "detail": str(exc)})
                    print(f"  HALT {jname}: {exc}", file=sys.stderr)
                    continue
                failures.extend(fails)
                for v in verdicts:
                    results.append({
                        "case": case.case_id, "arm": arm, "judge": jname,
                        "scored": v.scored, "estimate": v.estimate, "band": v.band,
                        "cited": list(v.evidence_ids),
                        "missingness_reason": v.missingness_reason,
                        "rationale": v.rationale,
                        "dossier_sha_inputs": list(dossier.observation_ids),
                        "distinct_original_sources": dossier.distinct_original_sources,
                        "telemetry": v.telemetry,
                    })
                    mark = v.estimate if v.scored else f"unscored/{v.missingness_reason}"
                    print(f"  {case.case_id:34} {arm:16} {jname:6} -> {mark}")

    findings = summarise(results)
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract": contract.as_dict(),
        "budgets": {k: v.report() for k, v in budgets.items()},
        "attempted": len(results) + len(failures),
        "succeeded": len(results),
        "failed": len(failures),
        "error_taxonomy": _taxonomy(failures),
        "results": results,
        "failures": failures,
        "findings": findings,
    }
    (out / "stress_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(findings, indent=2))
    print(f"\nwrote {out / 'stress_report.json'}")
    return 0


def _taxonomy(failures: list[dict]) -> dict[str, int]:
    tax: dict[str, int] = {}
    for f in failures:
        tax[f.get("error_type", "unknown")] = tax.get(f.get("error_type", "unknown"), 0) + 1
    return tax


def _by(results: list[dict], case: str) -> dict[str, list[dict]]:
    arms: dict[str, list[dict]] = {}
    for r in results:
        if r["case"] == case:
            arms.setdefault(r["arm"], []).append(r)
    return arms


def _mean(rows: list[dict]) -> float | None:
    vals = [r["estimate"] for r in rows if r["scored"] and r["estimate"] is not None]
    return statistics.mean(vals) if vals else None


def summarise(results: list[dict]) -> dict:
    """Turn raw scores into the question each case was asked to answer."""
    out: dict = {}

    a = _by(results, "S1_single_vs_multi")
    if a.get("strong_single") and a.get("weak_multi"):
        s, m = _mean(a["strong_single"]), _mean(a["weak_multi"])
        out["S1_single_vs_multi"] = {
            "strong_single_mean": s, "weak_multi_mean": m,
            "ordering_holds": None if None in (s, m) else s > m,
            "reading": "publication count imposed the ordering" if (
                s is not None and m is not None and s <= m
            ) else "the stronger substantive judgment scored higher",
        }

    a = _by(results, "S2_format_equivalence")
    means = {k: _mean(v) for k, v in a.items()}
    vals = [v for v in means.values() if v is not None]
    if vals:
        out["S2_format_equivalence"] = {
            "per_format": means, "spread": max(vals) - min(vals),
            "reading": "format may be acting as a ceiling; investigate"
            if max(vals) - min(vals) > 10 else "formats scored comparably",
        }

    a = _by(results, "S3_corroboration_no_new_judgment")
    if a.get("one_publisher") and a.get("three_publishers"):
        one, three = _mean(a["one_publisher"]), _mean(a["three_publishers"])
        out["S3_corroboration_no_new_judgment"] = {
            "one_publisher_mean": one, "three_publishers_mean": three,
            "delta": None if None in (one, three) else three - one,
            "reading": "corroboration moved the estimate" if (
                one is not None and three is not None and abs(three - one) > 5
            ) else "corroboration left the estimate where it was",
        }

    a = _by(results, "S4_contradiction")
    rows = a.get("contradictory", [])
    if rows:
        out["S4_contradiction"] = {
            "estimates": [r["estimate"] for r in rows],
            "rationales_name_both_placements": [
                ("obs_s4a" in r["rationale"] and "obs_s4b" in r["rationale"]) for r in rows
            ],
        }

    a = _by(results, "S5_empty_and_offtopic")
    out_s5 = {}
    for arm in ("empty", "offtopic"):
        rows = a.get(arm, [])
        if rows:
            out_s5[arm] = {
                "all_unscored": all(not r["scored"] for r in rows),
                "scores_if_any": [r["estimate"] for r in rows if r["scored"]],
            }
    if out_s5:
        out["S5_empty_and_offtopic"] = out_s5

    a = _by(results, "S6_identity_leakage")
    means = {k: _mean(v) for k, v in a.items()}
    vals = [v for v in means.values() if v is not None]
    if vals:
        # Report PER JUDGE. A pooled mean hides the case where one judge is
        # perfectly stable and the other moves, which is what actually happened.
        per_judge: dict[str, dict[str, float | None]] = {}
        for arm, rows in a.items():
            for r in rows:
                per_judge.setdefault(r["judge"], {})[arm] = r["estimate"]
        spreads = {
            j: (max(v.values()) - min(v.values()))
            for j, v in per_judge.items()
            if len(v) > 1 and None not in v.values()
        }
        worst = max(spreads.values()) if spreads else 0
        out["S6_identity_leakage"] = {
            "per_arm_pooled": means, "per_judge": per_judge,
            "per_judge_spread": spreads, "worst_spread": worst,
            "reading": (
                "no judge moved under a changed identity" if worst == 0
                else f"largest move under a changed identity was {worst} points; "
                     "compare against rater noise before calling it leakage"
            ),
        }

    a = _by(results, "S7_order_sensitivity")
    means = {k: _mean(v) for k, v in a.items()}
    vals = [v for v in means.values() if v is not None]
    if len(vals) == 2:
        out["S7_order_sensitivity"] = {
            "per_order": means, "spread": abs(vals[0] - vals[1]),
        }

    a = _by(results, "S8_volume_without_content")
    means = {k: _mean(v) for k, v in a.items()}
    vals = [v for v in means.values() if v is not None]
    if len(vals) == 2:
        out["S8_volume_without_content"] = {
            "per_arm": means, "spread": abs(vals[0] - vals[1]),
            "reading": "copy volume raised the score" if abs(vals[0] - vals[1]) > 0
            else "copy volume changed nothing",
        }
    return out


if __name__ == "__main__":
    raise SystemExit(main())
