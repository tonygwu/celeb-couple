#!/usr/bin/env python3
"""Merge every person-year grading into one canonical score each. FREE.

Reads the two judge caches and any extra grading files, normalises them into
grading records that carry model and timestamp provenance, and writes the
canonical mean per (person, year).

The operator's rule, 2026-09-16: keep every grading, and average them. A
person-year graded twice by Fable, once by Opus and once by Sonnet has a
canonical score that is the mean of those four.

Nothing here spends quota and nothing here overwrites a cache. The caches stay
exactly as the runs left them.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.artifacts import require                          # noqa: E402
from modules.pairing.canonical import (                                # noqa: E402
    canonical_scores, coverage, normalise_grading, refuse_pooled_contracts,
)

DEFAULT_CACHES = ("data/roster100/run/person_period_cache.json",
                  "data/roster100/run/person_period_cache_astra.json",
                  # the IMDb corpus, graded by Opus. A separate FILE, not a
                  # separate population: keys are (family, qid, period), so a
                  # person in both corpora gets one canonical score from all
                  # of their gradings.
                  "data/imdb/person_period_cache_opus.json")
DEFAULT_EXTRA = ("data/roster100/run/extra_gradings.json",)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Average every grading of a person-year into one canonical "
                    "score. Free.")
    ap.add_argument("--cache", action="append", default=None)
    ap.add_argument("--extra", action="append", default=None,
                    help="files shaped {'gradings': {key: entry}}")
    ap.add_argument("--exclude-model", action="append", default=None,
                    help="drop a model from the average WITHOUT re-grading, "
                         "e.g. --exclude-model claude-sonnet-5")
    ap.add_argument("--out", default="data/roster100/run/person_gradings.json")
    args = ap.parse_args()

    gradings = []
    for rel in (args.cache or DEFAULT_CACHES):
        if not (REPO / rel).exists():
            print(f"  (no {rel}; skipping)")
            continue
        for entry in require(REPO, rel).values():
            gradings.append(normalise_grading(entry, source=rel))
    for rel in (args.extra or DEFAULT_EXTRA):
        if not (REPO / rel).exists():
            print(f"  (no {rel}; skipping)")
            continue
        blob = json.loads((REPO / rel).read_text())
        for entry in blob["gradings"].values():
            gradings.append(normalise_grading(entry, source=rel))

    exclude = tuple(args.exclude_model or ())
    canon = canonical_scores(gradings, exclude_models=exclude)
    refuse_pooled_contracts(canon)
    cov = coverage(canon)

    by_model: dict[str, int] = {}
    undated = 0
    for g in gradings:
        by_model[g["model"]] = by_model.get(g["model"], 0) + 1
        if not g["graded_at_known"]:
            undated += 1

    print(f"gradings read: {len(gradings):,}")
    for m, n in sorted(by_model.items(), key=lambda kv: -kv[1]):
        print(f"    {m:<22} {n:>5}")
    print(f"  without a recorded grading time: {undated:,} "
          f"(runs before 2026-09-16 did not stamp one; NOT back-filled from mtime)")
    if exclude:
        print(f"  excluded from the average: {', '.join(exclude)}")
    print(f"canonical person-years: {cov['person_years']:,}")
    print(f"  by grading count: {cov['by_grading_count']}")
    print(f"  multiply graded:  {cov['multiply_graded']:,}"
          f"   mean spread {cov['mean_spread_where_multiple']}"
          f"   max {cov['max_spread']}")

    dest = REPO / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps({
        "coverage": cov, "gradings_by_model": by_model,
        "gradings_without_a_recorded_time": undated,
        "excluded_models": list(exclude),
        "canonical": {f"{q}|{p}": v for (q, p), v in sorted(canon.items())},
    }, indent=1))
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
