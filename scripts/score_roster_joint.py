#!/usr/bin/env python3
"""Score only the person-periods the roster-scale jointly covered pairings need.

The roster corpus has 131 observations over 127 person-periods. Scoring all of
them would cost 127 model calls to answer a question that five pairings decide,
so this scores only what those five need -- about nine dossiers.

The pairing that matters is the COMPARABLE one: Richard Gere and Cindy Crawford,
1992, both judged by the same kind of evidence. It would be the second
comparable pairing this project has, and the first outside the pilot cohort.
"""
from __future__ import annotations
import argparse, json, os, sys
from fractions import Fraction
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require                          # noqa: E402
from packages.llmkit.accounts import resolve_account            # noqa: E402
from packages.llmkit.budget import Budget, BudgetExhausted             # noqa: E402
from packages.llmkit.contract import STANDING_RUBRIC_VERSION, load_contract                     # noqa: E402
from packages.llmkit.judges import ClaudeJudge                         # noqa: E402
from packages.llmkit.manifest import RunManifest                       # noqa: E402
from packages.schema.records import (                                  # noqa: E402
    EvidenceType, Lineage, ListEdition, Observation)
from packages.temporal.dates import Precision, PreciseDate             # noqa: E402
from modules.analytics.comparability import classify_pairing           # noqa: E402
from modules.analytics.metrics import (                                # noqa: E402
    Pairing, PeriodExposure, as_estimate, gap)
from modules.consensus.dossier import build_dossier                    # noqa: E402
from modules.consensus.nearby import resolve_period                    # noqa: E402
from modules.consensus.score import score_dossier                      # noqa: E402

RUBRIC = REPO / "rubrics/standing/RUBRIC.md"
SCHEMA = REPO / "rubrics/standing/estimate.schema.json"


def main() -> int:
    ap = argparse.ArgumentParser(description='Score only what the roster-scale joint pairings need. SPENDS MODEL QUOTA.')
    ap.add_argument("--account", default=None,
                    help=("Claude Code config dir to run under. No default: "
                          "quota headroom moves between accounts. Run "
                          "`quotapick status` first, or set CELEB_ACCOUNT."))
    ap.add_argument("--max-calls", type=int, default=20)
    ap.add_argument("--out", default="data/roster100/run/joint_scores.json")
    args = ap.parse_args()

    obs = require(REPO, "data/roster100/observations/observations.json")
    joint = require(REPO, "data/roster100/run/joint_real_life.json")
    roster = require(REPO, "docs/roster-100.json")["people"]
    partners = require(REPO, "data/roster100/records/partner_universe.json")["people"]
    names = {p["wikidata_qid"]: p["display_name"] for p in roster + partners}
    by_name = {v: k for k, v in names.items()}

    editions, by_pp = {}, {}
    for e in obs["editions"]:
        editions[e["list_edition_id"]] = ListEdition(
            list_edition_id=e["list_edition_id"], publisher=e["publisher"],
            title=e["title"], source_url="https://en.wikipedia.org/",
            published_at=PreciseDate(e["published_at"],
                                     Precision(e["published_precision"]),
                                     e["list_edition_id"]),
            concerns_period=PreciseDate(e["concerns_period"], Precision.YEAR,
                                        e["list_edition_id"]),
            access_route="wikipedia-api", retrieved_at_utc=obs["generated_at_utc"],
            content_sha256=e["content_sha256"],
            candidate_set_described=e["candidate_set_described"],
            list_length=e["list_length"], licence=e.get("licence"),
            attribution=e.get("attribution"))
    have, shape_of = {}, {}
    for o in obs["observations"]:
        ed = editions[o["list_edition_id"]]
        by_pp.setdefault((o["person_id"], o["concerns_period"]), []).append(
            Observation(
                observation_id=o["observation_id"], person_id=o["person_id"],
                list_edition_id=o["list_edition_id"],
                evidence_type=EvidenceType(o["evidence_type"]),
                observed=o["observed"], concerns_period=ed.concerns_period,
                published_at=ed.published_at,
                lineage=Lineage(o["lineage"]["original_source"],
                                o["lineage"]["is_syndicated_copy"]),
                excerpt=o["excerpt"], excerpt_locator=o["excerpt_locator"],
                review_status=o["review_status"]))
        have.setdefault(o["person_id"], {})[o["concerns_period"]] = 1.0
        shape_of.setdefault((o["person_id"], o["concerns_period"]), set()).add(
            o["evidence_type"])

    # exactly the dossiers the jointly covered rows resolve to
    needed: set[tuple[str, str]] = set()
    plan = []
    for r in joint["rows"]:
        a, b = by_name.get(r["a"]), by_name.get(r["b"])
        if not a or not b:
            print(f"  SKIP {r['a']} + {r['b']}: unresolved id")
            continue
        ra = resolve_period(r["period"], have.get(a, {}))
        rb = resolve_period(r["period"], have.get(b, {}))
        if not (ra.scored and rb.scored):
            continue
        needed.add((a, ra.source_period))
        needed.add((b, rb.source_period))
        plan.append((r, a, ra.source_period, b, rb.source_period))

    print(f"jointly covered rows: {len(plan)}; dossiers needed: {len(needed)}")

    contract = load_contract(RUBRIC, SCHEMA, STANDING_RUBRIC_VERSION)
    rubric, schema = RUBRIC.read_text(), SCHEMA.read_text()
    judge = ClaudeJudge("fable", "claude-fable-5-1", config_dir=resolve_account(args.account))
    budget = Budget(max_calls=args.max_calls)
    manifest = RunManifest(stage_name="roster-joint", repo=REPO, args=vars(args),
                           contracts={"standing": contract.as_dict()},
                           caps={"max_calls": args.max_calls})
    stage = manifest.stage("score")
    out = REPO / args.out
    (out.parent / "raw_joint").mkdir(parents=True, exist_ok=True)

    est: dict[tuple[str, str], float | None] = {}
    for person, period in sorted(needed):
        stage.attempted += 1
        d = build_dossier(person, names.get(person, person), period,
                          list(by_pp.get((person, period), [])), editions)
        try:
            _, verdicts, fails = score_dossier(
                d, [judge], contract, rubric, schema, budget,
                out.parent / "raw_joint", timeout=900)
        except BudgetExhausted as exc:
            manifest.halt(str(exc)); print(f"  HALT {exc}"); break
        for f in fails:
            stage.record_failure(f["error_type"])
        v = next((v for v in verdicts if v.scored), None)
        est[(person, period)] = float(v.estimate) if v else None
        if v:
            stage.succeeded += 1
        else:
            stage.excluded += 1
        print(f"  {names.get(person, person)[:24]:24} {period} obs="
              f"{len(d.observation_ids)} -> {est[(person, period)]}")

    rows = []
    for r, a, ap_, b, bp in plan:
        ea, eb = est.get((a, ap_)), est.get((b, bp))
        if ea is None or eb is None:
            continue
        k = Pairing(f"rl_{r['period']}_{a}_{b}", a, b, "real_life",
                    (PeriodExposure(r["period"], Fraction(1), as_estimate(ea),
                                    as_estimate(eb), f"se_{a}_{ap_}",
                                    f"se_{b}_{bp}"),))
        g, gm = gap(k), gap(k.mirror())
        c = classify_pairing(k.pairing_id,
                             "+".join(sorted(shape_of.get((a, ap_), []))),
                             "+".join(sorted(shape_of.get((b, bp), []))))
        rows.append({"period": r["period"], "a": r["a"], "b": r["b"],
                     "a_estimate": ea, "b_estimate": eb,
                     "a_from": ap_, "b_from": bp,
                     "comparability": c.status, "a_shape": c.a_shape,
                     "b_shape": c.b_shape, "caveat": c.caveat,
                     "gap_a_view": float(g), "gap_b_view": float(gm),
                     "mirrors_exactly": g == -gm})
        flag = "" if c.comparable else f"  [{c.status}]"
        print(f"\n  {r['period']}  {r['a']} {ea}  +  {r['b']} {eb}")
        print(f"      gap {float(g):+.1f} / mirrored {float(gm):+.1f}  "
              f"mirrors exactly: {g == -gm}{flag}")

    stage.notes = {"pairings": len(rows),
                   "comparable": sum(1 for r in rows
                                     if r["comparability"] == "comparable")}
    out.write_text(json.dumps({"contract": contract.as_dict(),
                               "budget": budget.report(),
                               "pairings": rows}, indent=2))
    manifest.write(REPO / "data/roster100/manifests")
    print(f"\n{json.dumps(stage.notes)}\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
