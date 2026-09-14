#!/usr/bin/env python3
"""Repeat-score unchanged dossiers to measure how much a judge moves on its own.

Plan section 3.5 makes rater spread one of the three quantified components of
the sensitivity interval, and M0 never measured it.

The interesting case is NOT the award dossiers. Twelve of those scored exactly
92.0 with both families agreeing to the digit, so their rater spread is
plausibly zero and measuring it mostly confirms a ceiling. The ranked dossier is
where the judges actually differed, so it carries the most information per call.
"""
from __future__ import annotations
import argparse, json, statistics, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.budget import Budget, BudgetExhausted           # noqa: E402
from packages.llmkit.contract import load_contract                   # noqa: E402
from packages.llmkit.judges import ClaudeJudge, CodexJudge           # noqa: E402
from packages.llmkit.manifest import RunManifest                     # noqa: E402
from packages.llmkit.outputs import archive_previous, guard_output                     # noqa: E402
from packages.schema.records import (                                # noqa: E402
    EvidenceType, Lineage, ListEdition, Observation,
)
from packages.temporal.dates import Precision, PreciseDate           # noqa: E402
from modules.consensus.dossier import build_dossier                  # noqa: E402
from modules.consensus.score import score_dossier                    # noqa: E402

RUBRIC = REPO / "rubrics/standing/RUBRIC.md"
SCHEMA = REPO / "rubrics/standing/estimate.schema.json"

#: Fisher LSD multiplier for a difference of two means at 95%, 1.96 * sqrt(2).
LSD_MULTIPLIER = 2.77


def _rebuild(blob):
    editions, by_pp = {}, {}
    for e in blob["editions"]:
        editions[e["list_edition_id"]] = ListEdition(
            list_edition_id=e["list_edition_id"], publisher=e["publisher"],
            title=e["title"], source_url="https://en.wikipedia.org/",
            published_at=PreciseDate(e["published_at"],
                                     Precision(e["published_precision"]),
                                     e["list_edition_id"]),
            concerns_period=PreciseDate(e["concerns_period"], Precision.YEAR,
                                        e["list_edition_id"]),
            access_route="wikipedia-api", retrieved_at_utc=blob["generated_at_utc"],
            content_sha256=e["content_sha256"],
            candidate_set_described=e["candidate_set_described"],
            list_length=e["list_length"], licence=e.get("licence"),
            attribution=e.get("attribution"))
    for o in blob["observations"]:
        ed = editions[o["list_edition_id"]]
        by_pp.setdefault((o["person_id"], o["concerns_period"]), []).append(
            Observation(
                observation_id=o["observation_id"], person_id=o["person_id"],
                list_edition_id=o["list_edition_id"],
                evidence_type=EvidenceType(o["evidence_type"]), observed=o["observed"],
                concerns_period=ed.concerns_period, published_at=ed.published_at,
                lineage=Lineage(o["lineage"]["original_source"],
                                o["lineage"]["is_syndicated_copy"]),
                excerpt=o["excerpt"], excerpt_locator=o["excerpt_locator"],
                review_status=o["review_status"]))
    return editions, by_pp


def summarise(per_target: list[dict], all_judges: list[str]) -> dict:
    """Build the headline from the per-target repeats.

    Reports the least significant difference PER EVIDENCE SHAPE. The pooled
    figure is kept, and named as pooled, because it is what earlier documents
    quoted -- but it must not be the number anyone reaches for.

    Why: the first version averaged the within-judge SDs across every target
    and published one LSD. Of the two dossiers measured, the rank-shaped one
    varied (86, 86, 88, 86) and the award-shaped one did not (92 four times).
    Averaging 0.866 with 0.0 gives 0.433 and an LSD of 1.2, which was then
    applied to gaps between rank-shaped estimates -- the shape holding all of
    the measured variance. The pooled figure understated the noise floor for
    exactly the estimates it was used on.

    A shape whose every repeat returned the same value gets no LSD at all. Four
    identical draws from a low-variance process are indistinguishable from four
    draws from a zero-variance one, so publishing 0.0 would state as a finding
    something the sample cannot show.
    """
    contributing = sorted({j for row in per_target
                           for j, v in row["runs"].items() if v})
    missing = [j for j in all_judges if j not in contributing]

    sds = [s for row in per_target
           for s in row["per_judge_sd"].values() if s is not None]

    by_shape_sds: dict[str, list[float]] = {}
    for row in per_target:
        for s in row["per_judge_sd"].values():
            if s is not None:
                by_shape_sds.setdefault(row["shape"], []).append(s)

    by_shape, degenerate = {}, []
    for shape, vals in sorted(by_shape_sds.items()):
        mean_sd = statistics.mean(vals)
        all_flat = all(v == 0 for v in vals)
        if all_flat:
            degenerate.append(shape)
        by_shape[shape] = {
            "n_targets": len(vals),
            "mean_within_judge_sd": round(mean_sd, 3),
            "least_significant_difference_95pct": (
                None if all_flat else round(LSD_MULTIPLIER * mean_sd, 2)),
            "note": ("every repeat returned the same value; this sample cannot "
                     "distinguish low variance from none, so no LSD is quoted"
                     if all_flat else None),
        }

    caveat = (
        "Measured on a handful of dossiers, each carrying ONE observation. "
        "This is rater variance only. Task variance across different people "
        "and different evidence is larger and is not measured here. "
        "`mean_within_judge_sd` and `least_significant_difference_95pct` are "
        "POOLED across evidence shapes and are kept only for continuity with "
        "earlier documents: use `by_shape`, because the shapes do not have the "
        "same noise and pooling hides that."
    )
    if len(contributing) < 2:
        caveat += (f" MEASURED ON ONE JUDGE "
                   f"({', '.join(contributing) or 'none'}), so this figure "
                   f"describes one model family and not a panel.")
        if missing:
            caveat += (f" {', '.join(missing)} was requested and produced "
                       f"no runs.")

    return {
        "judges_requested": all_judges,
        "judges_that_contributed": contributing,
        "judges_with_no_runs": missing,
        "single_judge": len(contributing) < 2,
        "mean_within_judge_sd": round(statistics.mean(sds), 3) if sds else None,
        "least_significant_difference_95pct": (
            round(LSD_MULTIPLIER * statistics.mean(sds), 2) if sds else None),
        "lsd_multiplier": LSD_MULTIPLIER,
        "by_shape": by_shape,
        "shapes_with_degenerate_sample": degenerate,
        "caveat": caveat,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description='Repeat-score unchanged dossiers to measure rater spread. SPENDS MODEL QUOTA.')
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument("--ranked", type=int, default=1, metavar="N",
                    help=("How many rank-shaped dossiers to repeat. The LSD is "
                          "quoted per shape and the ranked shape holds all of "
                          "the measured variance, so this is the number that "
                          "decides how well the noise floor is known."))
    ap.add_argument("--award", type=int, default=1, metavar="N",
                    help="How many award-shaped dossiers to repeat.")
    ap.add_argument("--account", default="/Users/tonygwu/.claude-e")
    ap.add_argument("--max-calls-per-judge", type=int, default=12)
    ap.add_argument("--judges", default="fable,astra")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="overwrite an artifact that holds more repeats than this run")
    ap.add_argument("--out", default="data/pilot/run/rater_noise.json")
    ap.add_argument("--recompute", metavar="ARTIFACT", default=None,
                    help=("Re-derive the headline from the stored judge runs in "
                          "an existing artifact and rewrite it in place. Spends "
                          "NO quota: the plan's reproducibility mechanism is "
                          "replaying stored responses, not re-invoking a model."))
    args = ap.parse_args()

    if args.recompute:
        f = REPO / args.recompute
        blob = json.loads(f.read_text())
        targets = blob["targets"]
        requested = sorted({j for row in targets for j in row["runs"]})
        blob["headline"] = summarise(targets, requested)
        blob["headline"]["recomputed_from_stored_runs"] = True
        f.write_text(json.dumps(blob, indent=2))
        print(json.dumps(blob["headline"], indent=2))
        print(f"\nrewrote {f} from {len(targets)} stored targets; no model calls")
        return 0

    blob = json.loads((REPO / "data/pilot/observations/observations.json").read_text())
    cohort = json.loads((REPO / "docs/pilot-cohort.json").read_text())
    # Partners are not in the cohort file, so a cohort-only name map printed
    # bare Q-ids -- "Q32522 1996 [ranked]" rather than Jennifer Aniston -- and
    # that id would have gone into the artifact's `person` field and from there
    # into the report tables. gender_shape_confound.py already reads both.
    _partners = json.loads(
        (REPO / "data/pilot/records/partner_universe.json").read_text())["people"]
    names = {p["wikidata_qid"]: p["display_name"]
             for p in cohort["people"] + _partners}
    editions, by_pp = _rebuild(blob)

    # one ranked dossier and one award dossier, so the comparison is like-for-like
    ranked = [(k, v) for k, v in by_pp.items()
              if any(o.evidence_type is EvidenceType.ORDERED_RANK for o in v)]
    award = [(k, v) for k, v in by_pp.items()
             if all(o.evidence_type is EvidenceType.EDITORIAL_AWARD for o in v)]
    # Sample size is a choice, not a constant. It was `ranked[:1] + award[:1]`,
    # which is why the published LSD rested on a single ranked dossier.
    targets = ranked[:args.ranked] + award[:args.award]
    if not targets:
        print("no dossier matches the requested shapes; nothing to measure",
              file=sys.stderr)
        return 2
    plan = [(p, per, "ranked" if (p, per) in dict.fromkeys(k for k, _ in ranked)
             else "award") for (p, per), _ in targets]

    _wanted = [j.strip() for j in args.judges.split(",") if j.strip()]
    print(f"targets ({len(targets)}), {args.repeats} repeats each, "
          f"{len(_wanted)} judge(s) ({', '.join(_wanted)}):")
    for p, per, shape in plan:
        print(f"  {names.get(p, p):22} {per}  [{shape}]")
    calls = len(targets) * args.repeats * len(
        [j for j in args.judges.split(",") if j.strip()])
    print(f"planned model calls: {calls}")
    if args.dry_run:
        print("dry run; nothing spent")
        return 0

    # After the dry run, which writes nothing, and before spending anything:
    # refuse a run that would replace a richer result.
    guard_output(REPO / args.out, field="repeats", value=args.repeats,
                 force=args.force)

    _kept = archive_previous(REPO / args.out)
    if _kept is not None:
        print(f"  [archive] previous measurement kept at {_kept}")

    contract = load_contract(RUBRIC, SCHEMA, "standing-rubric-2.0")
    rubric, schema = RUBRIC.read_text(), SCHEMA.read_text()
    wanted = [j.strip() for j in args.judges.split(",") if j.strip()]
    judges = []
    if "fable" in wanted:
        judges.append(("fable", ClaudeJudge("fable", "claude-fable-5-1",
                                            config_dir=args.account)))
    if "astra" in wanted:
        judges.append(("astra", CodexJudge("astra", "gpt-6-astra", effort="high")))
    budgets = {n: Budget(max_calls=args.max_calls_per_judge) for n, _ in judges}
    manifest = RunManifest(stage_name="rater-noise", repo=REPO, args=vars(args),
                           contracts={"standing": contract.as_dict()},
                           caps={"max_calls_per_judge": args.max_calls_per_judge})
    stage = manifest.stage("repeat-score")
    raw = REPO / "data/pilot/run/raw_repeats"

    per_target = []
    for ((person, period), observations), (_, _, shape) in zip(targets, plan):
        d = build_dossier(person, names.get(person, person), period,
                          list(observations), editions)
        runs: dict[str, list[float]] = {}
        for jname, judge in judges:
            for r in range(args.repeats):
                stage.attempted += 1
                try:
                    budgets[jname].spend_call(f"{d.dossier_id}/{jname}/r{r}")
                except BudgetExhausted as exc:
                    stage.attempted -= 1
                    manifest.halt(str(exc)); print(f"  HALT {exc}"); break
                _, verdicts, fails = score_dossier(
                    d, [judge], contract, rubric, schema,
                    Budget(max_calls=1), raw / f"r{r}", timeout=900)
                for f in fails:
                    stage.record_failure(f["error_type"])
                for v in verdicts:
                    if v.scored:
                        stage.succeeded += 1
                        runs.setdefault(jname, []).append(float(v.estimate))
                    else:
                        stage.excluded += 1
        row = {"person": names.get(person, person), "period": period, "shape": shape,
               "runs": runs,
               "per_judge_sd": {j: (statistics.pstdev(v) if len(v) > 1 else None)
                                for j, v in runs.items()},
               "per_judge_mean": {j: (statistics.mean(v) if v else None)
                                  for j, v in runs.items()},
               "per_judge_range": {j: (max(v) - min(v) if v else None)
                                   for j, v in runs.items()}}
        per_target.append(row)
        print(f"  {row['person']:22} {period} [{shape}] runs={runs} "
              f"sd={row['per_judge_sd']}")

    headline = summarise(per_target, sorted(n for n, _ in judges))
    stage.notes = headline
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"contract": contract.as_dict(),
                               "repeats": args.repeats, "headline": headline,
                               "targets": per_target}, indent=2))
    mpath = manifest.write(REPO / "data/pilot/manifests")
    print("\n" + json.dumps(headline, indent=2))
    print(f"wrote {out}\nmanifest {mpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
