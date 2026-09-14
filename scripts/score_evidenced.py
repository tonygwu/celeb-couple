#!/usr/bin/env python3
"""Score every person-period that actually has evidence, then work the pairings."""
from __future__ import annotations
import json, sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.budget import Budget, BudgetExhausted                  # noqa: E402
from packages.llmkit.contract import load_contract                          # noqa: E402
from packages.llmkit.judges import ClaudeJudge, CodexJudge                  # noqa: E402
from packages.schema.records import (EvidenceType, Lineage, ListEdition,    # noqa: E402
                                     Observation)
from packages.temporal.dates import Precision, PreciseDate                  # noqa: E402
from modules.analytics.metrics import (Pairing, PeriodExposure,             # noqa: E402
                                       as_estimate, covered_share, gap)
from modules.consensus.dossier import build_dossier                         # noqa: E402
from modules.consensus.nearby import resolve_period                         # noqa: E402
from modules.consensus.score import score_dossier                           # noqa: E402

RUBRIC, SCHEMA = REPO / "rubrics/standing/RUBRIC.md", REPO / "rubrics/standing/estimate.schema.json"
obs_blob = json.loads((REPO / "data/pilot/observations/observations.json").read_text())
cohort = json.loads((REPO / "docs/pilot-cohort.json").read_text())
joint = json.loads((REPO / "data/pilot/run/joint_with_nearby.json").read_text())
names = {p["wikidata_qid"]: p["display_name"] for p in cohort["people"]}
_partners = REPO / "data/pilot/records/partner_universe.json"
if _partners.exists():
    names.update({p["wikidata_qid"]: p["display_name"]
                  for p in json.loads(_partners.read_text())["people"]})

editions = {}
for e in obs_blob["editions"]:
    editions[e["list_edition_id"]] = ListEdition(
        list_edition_id=e["list_edition_id"], publisher=e["publisher"], title=e["title"],
        source_url="https://en.wikipedia.org/",
        published_at=PreciseDate(e["published_at"], Precision(e["published_precision"]), e["list_edition_id"]),
        concerns_period=PreciseDate(e["concerns_period"], Precision.YEAR, e["list_edition_id"]),
        access_route="wikipedia-api", retrieved_at_utc=obs_blob["generated_at_utc"],
        content_sha256=e["content_sha256"], candidate_set_described=e["candidate_set_described"],
        list_length=e["list_length"], licence=e.get("licence"), attribution=e.get("attribution"))
by_pp = {}
for o in obs_blob["observations"]:
    ed = editions[o["list_edition_id"]]
    by_pp.setdefault((o["person_id"], o["concerns_period"]), []).append(Observation(
        observation_id=o["observation_id"], person_id=o["person_id"],
        list_edition_id=o["list_edition_id"], evidence_type=EvidenceType(o["evidence_type"]),
        observed=o["observed"], concerns_period=ed.concerns_period, published_at=ed.published_at,
        lineage=Lineage(o["lineage"]["original_source"], o["lineage"]["is_syndicated_copy"]),
        excerpt=o["excerpt"], excerpt_locator=o["excerpt_locator"], review_status=o["review_status"]))

contract = load_contract(RUBRIC, SCHEMA, "standing-rubric-2.0")
rt, st = RUBRIC.read_text(), SCHEMA.read_text()
import os
_JUDGES = os.environ.get("CELEB_JUDGES", "fable,astra").split(",")
judges = []
if "fable" in _JUDGES:
    judges.append(("fable", ClaudeJudge("fable", "claude-fable-5-1",
                                        config_dir="/Users/tonygwu/.claude-e")))
if "astra" in _JUDGES:
    judges.append(("astra", CodexJudge("astra", "gpt-6-astra", effort="high")))
_CAP = int(os.environ.get("CELEB_MAX_CALLS", "60"))
budgets = {"fable": Budget(max_calls=_CAP), "astra": Budget(max_calls=_CAP)}
out = REPO / "data/pilot/run"; (out / "raw").mkdir(parents=True, exist_ok=True)

estimates, records, failures, halted = {}, [], [], []
for (person, period), observations in sorted(by_pp.items(), key=lambda kv: (kv[0][1], kv[0][0])):
    d = build_dossier(person, names.get(person, person), period, list(observations), editions)
    per_judge, rationales = {}, {}
    effort_flags = {}
    for jname, judge in judges:
        try:
            est, verdicts, fails = score_dossier(d, [judge], contract, rt, st,
                                                 budgets[jname], out / "raw",
                                                 timeout=900)
        except BudgetExhausted as exc:
            # A halt is reported as a halt. Crashing here would lose every score
            # already computed in this run, which is the opposite of what a cap
            # is for.
            halted.append(str(exc))
            print(f"  HALT {jname}: {exc}")
            continue
        failures.extend(fails)
        for v in verdicts:
            if v.scored:
                per_judge[jname] = float(v.estimate); rationales[jname] = v.rationale
                effort_flags.setdefault(jname, []).append(
                    v.telemetry.get("effort_took_effect"))
    value = sum(per_judge.values()) / len(per_judge) if per_judge else None
    estimates[(person, period)] = value
    gapj = (max(per_judge.values()) - min(per_judge.values())) if len(per_judge) > 1 else None
    records.append({"person": names.get(person, person), "person_id": person, "period": period,
                    "observations": len(d.observation_ids), "estimate": value,
                    "judges": per_judge, "across_judges_gap": gapj,
                    "needs_adjudication": bool(gapj and gapj > 10),
                    "support_level": "single_source" if d.distinct_original_sources <= 1 else "multi",
                    "effort_took_effect": effort_flags,
                    "rationales": rationales})
    print(f"  {names.get(person, person)[:20]:20} {period}  obs={len(d.observation_ids)}  "
          f"-> {value}  {per_judge}  gap={gapj}")

# Persist the scores BEFORE deriving pairings. Every one of these cost a model
# call, and a crash in the cheap derived step below used to throw all of them
# away: 34 scores lost to a KeyError on a partner's name.
out.mkdir(parents=True, exist_ok=True)
(out / "person_period_scores.json").write_text(json.dumps(
    {"person_periods": records, "failures": failures, "halted": halted}, indent=2))
print(f"\n  [checkpoint] wrote {len(records)} person-period scores before pairings")

pairings = []
for j in joint["jointly_covered"]:
    # joint_coverage already carries the ids; reverse-looking-up by display
    # name broke the moment a partner appeared, because names held cohort only.
    a_id = j.get("a_qid") or next((q for q, n in names.items() if n == j["a"]), None)
    b_id = j.get("b_qid") or next((q for q, n in names.items() if n == j["b"]), None)
    if a_id is None or b_id is None:
        print(f"  SKIP pairing {j.get('work') or 'relationship'}: unresolved id")
        continue
    ea, eb = estimates.get((a_id, j["a_src"])), estimates.get((b_id, j["b_src"]))
    k = Pairing(f"{j['domain']}_{j['period']}_{a_id}_{b_id}", a_id, b_id, j["domain"],
                (PeriodExposure(j["period"], Fraction(1), as_estimate(ea), as_estimate(eb),
                                f"se_{a_id}_{j['a_src']}", f"se_{b_id}_{j['b_src']}"),))
    g, gm = gap(k), gap(k.mirror())
    pairings.append({"work": j["work"], "domain": j["domain"], "period": j["period"],
                     "focal_male": j["a"], "female": j["b"],
                     "male_estimate": ea, "female_estimate": eb,
                     "male_estimate_from": j["a_src"], "female_estimate_from": j["b_src"],
                     "period_support": "nearby_period" if j["a_dist"] or j["b_dist"] else "contemporaneous",
                     "covered_share": str(covered_share(k)),
                     "gap_mens_view": None if g is None else float(g),
                     "gap_womens_view": None if gm is None else float(gm),
                     "mirrors_exactly": g is not None and g == -gm,
                     "verification": "co-appearance only; ROMANCE UNVERIFIED"})
    print(f"\n  {j['work']} ({j['period']}, {j['domain']})")
    print(f"    {j['a']:18} {ea}  (estimate from {j['a_src']}, reused)")
    print(f"    {j['b']:18} {eb}  (estimate from {j['b_src']}, reused)")
    print(f"    gap in men's view  {float(g):+.1f}   gap in women's view {float(gm):+.1f}"
          f"   mirrors exactly: {g == -gm}")

report = {"generated_at_utc": datetime.now(timezone.utc).isoformat(),
          "contract": contract.as_dict(),
          "budgets": {k: v.report() for k, v in budgets.items()},
          "halted": halted,
          "reconciliation": {"person_periods_with_evidence": len(by_pp),
                             "scored": sum(1 for r in records if r["estimate"] is not None),
                             "model_calls": sum(b.calls_made for b in budgets.values()),
                             "failed_calls": len(failures)},
          "person_periods": records, "scored_pairings": pairings, "failures": failures}
(out / "evidenced_scores.json").write_text(json.dumps(report, indent=2))
print("\n" + json.dumps(report["reconciliation"], indent=2))
print(f"wrote {out / 'evidenced_scores.json'}")
