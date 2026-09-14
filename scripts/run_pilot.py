#!/usr/bin/env python3
"""M0 pilot: select bounded pairings, score their person-periods, report coverage.

Reports BOTH coverage numbers the plan asks for:
  - person-period availability: does each person-year have any evidence?
  - joint pairing-period coverage: are BOTH sides scored over the same periods?
Only the second one decides whether a pairing contributes, and a pairing with
one side unscored is removed from both mirrored gender views.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.budget import Budget, BudgetExhausted             # noqa: E402
from packages.llmkit.contract import load_contract                     # noqa: E402
from packages.llmkit.judges import ClaudeJudge, CodexJudge             # noqa: E402
from packages.schema.records import (                                  # noqa: E402
    EvidenceType, Lineage, ListEdition, Observation,
)
from packages.temporal.dates import Precision, PreciseDate             # noqa: E402
from modules.analytics.metrics import (                                # noqa: E402
    Pairing, PeriodExposure, as_estimate, covered_share, gap,
)
from modules.consensus.dossier import build_dossier                    # noqa: E402
from modules.consensus.score import score_dossier                      # noqa: E402

RUBRIC = REPO / "rubrics/standing/RUBRIC.md"
SCHEMA = REPO / "rubrics/standing/estimate.schema.json"
MAX_PERIODS_PER_PAIRING = 3


def _load(path: str) -> dict:
    return json.loads((REPO / path).read_text())


def _rebuild_observations(blob: dict) -> tuple[dict[str, ListEdition], dict[tuple[str, str], list[Observation]]]:
    editions = {}
    for e in blob["editions"]:
        editions[e["list_edition_id"]] = ListEdition(
            list_edition_id=e["list_edition_id"], publisher=e["publisher"],
            title=e["title"],
            source_url="https://en.wikipedia.org/",
            published_at=PreciseDate(
                e["published_at"], Precision(e["published_precision"]), e["list_edition_id"]),
            concerns_period=PreciseDate(
                e["concerns_period"], Precision.YEAR, e["list_edition_id"]),
            access_route="wikipedia-api", retrieved_at_utc=blob["generated_at_utc"],
            content_sha256=e["content_sha256"],
            candidate_set_described=e["candidate_set_described"],
            list_length=e["list_length"], licence=e.get("licence"),
            attribution=e.get("attribution"),
        )
    by_person_period: dict[tuple[str, str], list[Observation]] = {}
    for o in blob["observations"]:
        ed = editions[o["list_edition_id"]]
        obs = Observation(
            observation_id=o["observation_id"], person_id=o["person_id"],
            list_edition_id=o["list_edition_id"],
            evidence_type=EvidenceType(o["evidence_type"]), observed=o["observed"],
            concerns_period=ed.concerns_period, published_at=ed.published_at,
            lineage=Lineage(o["lineage"]["original_source"],
                            o["lineage"]["is_syndicated_copy"]),
            excerpt=o["excerpt"], excerpt_locator=o["excerpt_locator"],
            review_status=o["review_status"],
        )
        by_person_period.setdefault((o["person_id"], o["concerns_period"]), []).append(obs)
    return editions, by_person_period


def _pick_periods(years: list[int]) -> list[str]:
    """At most three representative periods: first, middle, last."""
    if not years:
        return []
    if len(years) <= MAX_PERIODS_PER_PAIRING:
        return [str(y) for y in years]
    return [str(years[0]), str(years[len(years) // 2]), str(years[-1])]


def main() -> int:
    ap = argparse.ArgumentParser(description='Bounded pairing selection and coverage for the pilot. SPENDS MODEL QUOTA.')
    ap.add_argument("--judges", default="fable,astra")
    ap.add_argument("--fable-account", default="/Users/tonygwu/.claude-e")
    ap.add_argument("--max-fable", type=int, default=40)
    ap.add_argument("--max-astra", type=int, default=28)
    ap.add_argument("--max-dossiers", type=int, default=50)
    ap.add_argument("--max-pairings", type=int, default=8)
    ap.add_argument("--as-of", default="2026-09-14")
    ap.add_argument("--out", default="data/pilot/run")
    args = ap.parse_args()

    cohort = _load("docs/pilot-cohort.json")
    names = {p["wikidata_qid"]: p["display_name"] for p in cohort["people"]}
    gender = {p["wikidata_qid"]: p["gender_category"] for p in cohort["people"]}
    episodes = _load("data/pilot/records/episodes.json")
    onscreen = _load("data/pilot/records/onscreen_candidates.json")
    obs_blob = _load("data/pilot/observations/observations.json")
    editions, by_pp = _rebuild_observations(obs_blob)

    # ---- select bounded pairings, spanning both domains and several eras ----
    selected: list[dict] = []
    real = [e for e in episodes["episodes"] if e["scorable"] and e["adult_years"]]
    real.sort(key=lambda e: -len(e["adult_years"]))
    for e in real[: args.max_pairings // 2]:
        selected.append({
            "pairing_id": e["episode_id"], "domain": "real_life",
            "a": e["subject_qid"], "b": e["partner_qid"],
            "a_name": e["subject_name"], "b_name": e["partner_label"],
            "periods": _pick_periods(e["adult_years"]),
            "verification": "wikidata candidate, UNVERIFIED",
        })
    films = [c for c in onscreen["candidates"] if c["release"][:4].isdigit()]
    films.sort(key=lambda c: c["release"])
    step = max(1, len(films) // (args.max_pairings - len(selected)))
    for c in films[::step][: args.max_pairings - len(selected)]:
        y = c["release"][:4]
        selected.append({
            "pairing_id": f"osp_{c['work_qid']}_{c['male_qid']}_{c['female_qid']}",
            "domain": "on_screen", "a": c["male_qid"], "b": c["female_qid"],
            "a_name": c["male"], "b_name": c["female"], "periods": [y],
            "work": c["title"],
            "verification": "co-appearance only, ROMANCE UNVERIFIED",
        })

    needed = sorted({(p, per) for s in selected for p in (s["a"], s["b"])
                     for per in s["periods"]})
    if len(needed) > args.max_dossiers:
        needed = needed[: args.max_dossiers]
    needed_set = set(needed)

    # ---- score ----
    contract = load_contract(RUBRIC, SCHEMA, "standing-rubric-2.0")
    rubric_text, schema_text = RUBRIC.read_text(), SCHEMA.read_text()
    judges = []
    if "fable" in args.judges:
        judges.append(("fable", ClaudeJudge("fable", "claude-fable-5-1",
                                            config_dir=args.fable_account)))
    if "astra" in args.judges:
        judges.append(("astra", CodexJudge("astra", "gpt-6-astra", effort="high")))
    budgets = {"fable": Budget(max_calls=args.max_fable),
               "astra": Budget(max_calls=args.max_astra)}

    out = Path(REPO / args.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    estimates: dict[tuple[str, str], float | None] = {}
    records, failures, short_circuited = [], [], 0

    for person, period in needed:
        observations = by_pp.get((person, period), [])
        dossier = build_dossier(person, names.get(person, person), period,
                                list(observations), editions)
        if dossier.is_empty:
            short_circuited += 1
            estimates[(person, period)] = None
            records.append({"person": names.get(person, person), "person_id": person,
                            "period": period, "estimate": None,
                            "missingness_reason": "no_observations",
                            "judges": {}, "observations": 0, "model_calls": 0})
            continue
        per_judge: dict[str, float] = {}
        for jname, judge in judges:
            try:
                est, verdicts, fails = score_dossier(
                    dossier, [judge], contract, rubric_text, schema_text,
                    budgets[jname], out / "raw", timeout=900)
            except BudgetExhausted as exc:
                failures.append({"person": person, "period": period, "judge": jname,
                                 "error_type": "budget_cap_reached", "detail": str(exc)})
                continue
            failures.extend(fails)
            for v in verdicts:
                if v.scored:
                    per_judge[jname] = float(v.estimate)
        value = sum(per_judge.values()) / len(per_judge) if per_judge else None
        estimates[(person, period)] = value
        records.append({
            "person": names.get(person, person), "person_id": person,
            "period": period, "estimate": value, "judges": per_judge,
            "observations": len(dossier.observation_ids),
            "model_calls": len(judges),
            "missingness_reason": None if value is not None else "all_rejected_in_review",
        })
        print(f"  {names.get(person, person)[:20]:20} {period}  obs={len(dossier.observation_ids)} "
              f"-> {value if value is not None else 'unscored'}  {per_judge}")

    # ---- coverage, the two numbers that matter ----
    pairing_rows = []
    for s in selected:
        periods = [p for p in s["periods"] if (s["a"], p) in needed_set]
        exposures = []
        q = Fraction(1, len(periods)) if periods else Fraction(0)
        for p in periods:
            exposures.append(PeriodExposure(
                p, q, as_estimate(estimates.get((s["a"], p))),
                as_estimate(estimates.get((s["b"], p))),
                f"se_{s['a']}_{p}", f"se_{s['b']}_{p}",
            ))
        k = Pairing(s["pairing_id"], s["a"], s["b"], s["domain"], tuple(exposures))
        cs, g = covered_share(k), gap(k)
        pairing_rows.append({
            **{key: s[key] for key in ("pairing_id", "domain", "a_name", "b_name",
                                       "verification")},
            "work": s.get("work"),
            "periods": periods,
            "a_scored": [p for p in periods if estimates.get((s["a"], p)) is not None],
            "b_scored": [p for p in periods if estimates.get((s["b"], p)) is not None],
            "covered_share": str(cs),
            "gap": None if g is None else float(g),
            "mirrored_gap": None if g is None else float(-g),
            "scored": g is not None,
        })

    scored_pp = sum(1 for r in records if r["estimate"] is not None)
    by_gender_scored = {}
    for r in records:
        gcat = gender.get(r["person_id"], "partner_outside_cohort")
        d = by_gender_scored.setdefault(gcat, {"person_periods": 0, "scored": 0})
        d["person_periods"] += 1
        d["scored"] += 1 if r["estimate"] is not None else 0

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_as_of": args.as_of,
        "contract": contract.as_dict(),
        "bounds": {"max_dossiers": args.max_dossiers, "max_pairings": args.max_pairings,
                   "max_periods_per_pairing": MAX_PERIODS_PER_PAIRING},
        "budgets": {k: v.report() for k, v in budgets.items()},
        "reconciliation": {
            "person_periods_needed": len(needed),
            "short_circuited_empty": short_circuited,
            "sent_to_judges": len(needed) - short_circuited,
            "scored": scored_pp,
            "unscored": len(needed) - scored_pp,
            "failed_calls": len(failures),
        },
        "error_taxonomy": {f["error_type"]: sum(
            1 for x in failures if x["error_type"] == f["error_type"]) for f in failures},
        "person_period_coverage": {
            "total": len(records), "scored": scored_pp,
            "rate": round(scored_pp / len(records), 3) if records else 0,
            "by_gender": by_gender_scored,
        },
        "joint_pairing_coverage": {
            "pairings": len(pairing_rows),
            "scored": sum(1 for r in pairing_rows if r["scored"]),
            "rate": round(sum(1 for r in pairing_rows if r["scored"]) / len(pairing_rows), 3)
            if pairing_rows else 0,
            "by_domain": {
                d: {
                    "pairings": sum(1 for r in pairing_rows if r["domain"] == d),
                    "scored": sum(1 for r in pairing_rows if r["domain"] == d and r["scored"]),
                }
                for d in ("real_life", "on_screen")
            },
        },
        "person_periods": records,
        "pairings": pairing_rows,
        "failures": failures,
    }
    (out / "pilot_report.json").write_text(json.dumps(report, indent=2))
    print("\nreconciliation:", json.dumps(report["reconciliation"], indent=2))
    print("person-period coverage:", json.dumps(report["person_period_coverage"], indent=2))
    print("joint pairing coverage:", json.dumps(report["joint_pairing_coverage"], indent=2))
    print(f"\nwrote {out / 'pilot_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
