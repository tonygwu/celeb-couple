#!/usr/bin/env python3
"""Which characters in each seed film are a couple. SPENDS MODEL QUOTA.

One call per (film, judge family), CACHED. A film already in the cache costs
nothing, so this is safe to stop and restart, and safe to widen later.

MODEL CHOICE. This is factual recall about a film, not an appearance judgment,
so it does NOT need Fable and must not spend Fable's separate weekly allowance.
Measured on the same ten films: Opus matched Fable everywhere and beat it once,
while Sonnet failed four of six checks -- it emitted Armageddon's father and
daughter as a couple, missed Cristin Milioti in The Wolf of Wall Street, missed
Julia Roberts and Alec Baldwin in Notting Hill, and paired Brooklyn Decker with
the wrong actor in Just Go with It. Two of those misses would have silently
deleted real board rows. Hence claude-opus-5 by default.

The appearance judgment stays film-blind (plan v4 4a). This stage decides WHO
gets scored together. It never sees or influences a score.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.accounts import resolve_account                   # noqa: E402
from packages.llmkit.artifacts import require                          # noqa: E402
from packages.llmkit.contract import COUPLES_RUBRIC_VERSION, load_contract  # noqa: E402
from packages.llmkit.judges import ClaudeJudge, JudgeError             # noqa: E402
from modules.pairing.couples import (                                  # noqa: E402
    CoupleVerdictError, board_pairs, build_prompt, cache_key,
    excluded_pairs, parse_couples_verdict,
)

RUBRIC = REPO / "rubrics/couples/COUPLES.md"
SCHEMA = REPO / "rubrics/couples/couples.schema.json"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Identify the couples in each seed film. SPENDS MODEL QUOTA.")
    ap.add_argument("--account", default=None,
                    help="Claude Code config dir. No default: quota headroom moves "
                         "between accounts. Run `quotapick status` first. Use "
                         "'default' for the account bare `claude` uses.")
    ap.add_argument("--model", default="claude-opus-5")
    ap.add_argument("--graph", default="data/imdb/seed_graph.json")
    ap.add_argument("--cache", default="data/imdb/couples_cache.json")
    ap.add_argument("--limit", type=int, default=None,
                    help="grade at most N uncached films, most-voted first")
    ap.add_argument("--backlog-only", action="store_true",
                    help="print what is uncached and exit. Spends nothing.")
    args = ap.parse_args()

    graph = require(REPO, args.graph)
    films, cast, name_of = graph["films"], graph["cast"], graph["name_of"]
    family = args.model.split("-")[1]

    cache_path = REPO / args.cache
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}

    order = sorted(films, key=lambda t: -films[t]["votes"])
    todo = [t for t in order if cache_key(t, family) not in cache]
    print(f"{len(films):,} seed films, family {family!r}")
    print(f"  cached already: {len(films) - len(todo):,}")
    print(f"  BACKLOG:        {len(todo):,}")
    if args.backlog_only:
        for t in todo[:20]:
            print(f"    {films[t]['votes']:>9,} votes  {films[t]['title']} ({films[t]['year']})")
        if len(todo) > 20:
            print(f"    ... and {len(todo) - 20:,} more")
        return 0
    if args.limit is not None:
        todo = todo[:args.limit]
    if not todo:
        print("nothing to do")
        return 0

    contract = load_contract(RUBRIC, SCHEMA, COUPLES_RUBRIC_VERSION)
    rubric = RUBRIC.read_text()
    judge = ClaudeJudge(family, args.model, config_dir=resolve_account(args.account))

    attempted = succeeded = failed = 0
    taxonomy: dict[str, int] = {}
    for i, t in enumerate(todo, 1):
        attempted += 1
        f = films[t]
        prompt = build_prompt(f["title"], f["year"], cast[t], rubric, name_of)
        try:
            res = judge(prompt, timeout=300)
            verdict = parse_couples_verdict(res.text)
        except (JudgeError, CoupleVerdictError) as exc:
            failed += 1
            kind = getattr(exc, "error_type", type(exc).__name__)
            taxonomy[kind] = taxonomy.get(kind, 0) + 1
            print(f"  [{i}/{len(todo)}] {f['title'][:34]:<35} FAILED {kind}", flush=True)
            continue
        keep, drop = board_pairs(verdict), excluded_pairs(verdict)
        cache[cache_key(t, family)] = {
            "tconst": t, "family": family, "model": args.model,
            "title": f["title"], "year": f["year"], "votes": f["votes"],
            "contract": contract.as_dict(),
            "pairs": verdict["pairs"], "note": verdict.get("note", ""),
            "n_board": len(keep), "n_excluded": len(drop),
            "graded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        # Write after EVERY call. A run that dies at 200 of 300 keeps its 200.
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=1))
        succeeded += 1
        print(f"  [{i}/{len(todo)}] {f['title'][:34]:<35} "
              f"{len(keep)} board, {len(drop)} incidental", flush=True)

    print(f"\nattempted {attempted}  succeeded {succeeded}  failed {failed}  {taxonomy}")
    if attempted != succeeded + failed:
        print(f"  !! RECONCILIATION: {attempted - succeeded - failed} unaccounted for")
    still = sum(1 for t in order if cache_key(t, family) not in cache)
    print(f"cache holds {len(cache):,} entries; {still:,} still on the backlog")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
