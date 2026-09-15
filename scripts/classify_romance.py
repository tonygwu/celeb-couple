#!/usr/bin/env python3
"""Classify the on-screen candidates: is it a romance, or just the same film?"""
from __future__ import annotations
import argparse, json, sys, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.accounts import resolve_account            # noqa: E402
from packages.llmkit.budget import Budget, BudgetExhausted            # noqa: E402
from packages.llmkit.contract import ROMANCE_RUBRIC_VERSION, load_contract                    # noqa: E402
from packages.llmkit.judges import ClaudeJudge, JudgeError            # noqa: E402
from packages.llmkit.manifest import RunManifest                      # noqa: E402
from modules.records.romance import (                                 # noqa: E402
    PlotUnavailable, build_prompt, fetch_cast, fetch_plot, parse_verdict,
    title_for_qid,
)

RUBRIC = REPO / "rubrics/romance/ROMANCE.md"
SCHEMA = REPO / "rubrics/romance/romance.schema.json"


def main() -> int:
    ap = argparse.ArgumentParser(description='Classify whether each co-starring pair is a romance in the film. SPENDS MODEL QUOTA.')
    ap.add_argument("--account", default=None,
                    help=("Claude Code config dir to run under. No default: "
                          "quota headroom moves between accounts. Run "
                          "`quotapick status` first, or set CELEB_ACCOUNT."))
    ap.add_argument("--model", default="claude-fable-5-1")
    ap.add_argument("--max-calls", type=int, default=25)
    ap.add_argument("--out", default="data/pilot/records/romance.json")
    args = ap.parse_args()

    cands = json.loads(
        (REPO / "data/pilot/records/onscreen_candidates.json").read_text())["candidates"]
    contract = load_contract(RUBRIC, SCHEMA, ROMANCE_RUBRIC_VERSION)
    rubric, schema = RUBRIC.read_text(), SCHEMA.read_text()
    judge = ClaudeJudge("fable", args.model, config_dir=resolve_account(args.account))
    budget = Budget(max_calls=args.max_calls)
    manifest = RunManifest(stage_name="romance", repo=REPO, args=vars(args),
                           contracts={"romance": contract.as_dict()},
                           caps={"max_calls": args.max_calls})
    stage = manifest.stage("classify")
    raw_dir = REPO / "data/pilot/records/raw_romance"
    raw_dir.mkdir(parents=True, exist_ok=True)

    results = []
    for c in cands:
        stage.attempted += 1
        label = f"{c['title']} ({c['male']} + {c['female']})"
        # No fallback to c["title"]. Guessing the article from the film's
        # title is what sent 13 of 20 candidates to the wrong subject -- Pearl
        # Harbor the harbour, Elektra the Greek tragedy -- and each returned a
        # real article with no plot, indistinguishable from a genuinely missing
        # one. `or c["title"]` quietly restored that path whenever the sitelink
        # lookup came back empty, and the artifact could not tell a resolved
        # title from a guessed one: 8 of 20 records have page == title either
        # way.
        try:
            page = title_for_qid(c["work_qid"])
        except Exception as exc:
            # Was outside the try below, so a network blip here killed the
            # whole batch instead of costing one candidate.
            stage.record_failure("transient_retryable")
            results.append({**c, "wikipedia_page": None,
                            "page_resolved_from": None,
                            "classification": "cannot_tell", "qualifies": False,
                            "exclusion": f"sitelink lookup failed: {exc}"})
            print(f"  FAIL  {label[:60]:60} sitelink lookup: {exc}")
            continue
        if not page:
            stage.excluded += 1
            results.append({**c, "wikipedia_page": None,
                            "page_resolved_from": None,
                            "classification": "cannot_tell", "qualifies": False,
                            "exclusion": "no English Wikipedia sitelink for "
                                         f"{c['work_qid']}"})
            print(f"  SKIP  {label[:60]:60} no enwiki sitelink")
            continue
        try:
            plot, plot_sha = fetch_plot(page)
        except PlotUnavailable as exc:
            stage.excluded += 1
            results.append({**c, "wikipedia_page": page,
                            "classification": "cannot_tell",
                            "qualifies": False, "exclusion": str(exc)})
            print(f"  SKIP  {label[:60]:60} {exc}")
            continue
        except Exception as exc:
            stage.record_failure("transient_retryable")
            results.append({**c, "classification": "cannot_tell",
                            "qualifies": False, "exclusion": f"fetch failed: {exc}"})
            print(f"  FAIL  {label[:60]:60} {exc}")
            continue

        try:
            cast = fetch_cast(page)
            cast_error = None
        except Exception as exc:
            # A silent {} here reverts the classifier to the exact condition
            # that produced 15 of 20 `cannot_tell` earlier: a prompt naming
            # ACTORS against a plot that names CHARACTERS. The verdicts then
            # look like a data problem rather than a fetch problem, which is
            # how that took a full investigation to diagnose the first time.
            cast, cast_error = {}, f"{type(exc).__name__}: {exc}"
            print(f"  CAST FAIL {label[:56]:56} {exc}")
        prompt = build_prompt(rubric, schema, c["title"], c["male"], c["female"],
                              plot, cast)
        try:
            budget.spend_call(label)
        except BudgetExhausted as exc:
            manifest.halt(str(exc))
            print(f"  HALT  {exc}")
            break
        try:
            res = judge(prompt, timeout=600)
        except JudgeError as exc:
            stage.record_failure(exc.error_type)
            results.append({**c, "classification": "cannot_tell", "qualifies": False,
                            "exclusion": exc.detail})
            print(f"  FAIL  {label[:60]:60} {exc.error_type}")
            continue
        (raw_dir / f"{c['work_qid']}_{c['male_qid']}_{c['female_qid']}.txt").write_text(res.text)
        try:
            v = parse_verdict(res.text, c["title"], plot, plot_sha)
        except ValueError as exc:
            stage.record_failure("schema_validation_failed")
            results.append({**c, "classification": "cannot_tell", "qualifies": False,
                            "exclusion": f"parse: {exc}"})
            print(f"  FAIL  {label[:60]:60} parse: {exc}")
            continue
        stage.succeeded += 1
        results.append({**c, "wikipedia_page": page,
                        "page_resolved_from": "wikidata_sitelink",
                        "cast_mapped": bool(cast.get(c["male"]) and cast.get(c["female"])),
                        "cast_error": cast_error,
                        **v.as_dict()})
        mark = "ROMANCE" if v.qualifies else v.classification
        mapped = "cast+" if cast.get(c["male"]) and cast.get(c["female"]) else "cast?"
        print(f"  {mark:22} {label[:52]:52} {mapped} grounded={v.grounded}")
        time.sleep(0.3)

    qualifying = [r for r in results if r.get("qualifies")]
    stage.notes = {
        "candidates": len(cands), "classified": stage.succeeded,
        "qualifying_romances": len(qualifying),
        "cast_mapped": sum(1 for r in results if r.get("cast_mapped")),
        # A cast the fetch FAILED to retrieve is a different thing from a film
        # whose article has no cast section. Both leave the prompt without
        # characters; only one is fixable by retrying.
        "cast_fetch_failed": sum(1 for r in results if r.get("cast_error")),
        "no_enwiki_sitelink": sum(
            1 for r in results if r.get("exclusion", "").startswith("no English")),
        "by_classification": {
            k: sum(1 for r in results if r.get("classification") == k)
            for k in sorted({r.get("classification") for r in results if r.get("classification")})
        },
    }
    out = REPO / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated_at_utc": manifest.started_at_utc,
        "contract": contract.as_dict(),
        "note": ("Classified from the Wikipedia plot section only. A verdict whose "
                 "quote is not found in that text is downgraded to cannot_tell, "
                 "because only reciprocal_romance puts a couple on a board."),
        "counts": stage.notes, "candidates": results,
    }, indent=2))
    mpath = manifest.write(REPO / "data/pilot/manifests")
    print(f"\n{json.dumps(stage.notes, indent=2)}")
    print(f"wrote {out}\nmanifest {mpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
