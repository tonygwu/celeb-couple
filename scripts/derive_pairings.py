#!/usr/bin/env python3
"""Derive every pairing gap from the cached person-year scores. Read-only, free.

This is where the cache pays off. A pairing's gap is now a SUBTRACTION of two
cached scores rather than a model call, so adding a pairing between two people
already in the cache costs nothing at all.

Output is shaped exactly like `pairing_scores.json`, so `build_boards.py` and
everything downstream read it without changes.

A pairing whose two people are not BOTH cached is emitted with `gap: null` and a
reason. It is not dropped: a pairing missing from the board because nobody
judged one of its people is a different thing from one judged and found even,
and the artifact has to be able to tell them apart.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.artifacts import require          # noqa: E402
from modules.pairing.person import cache_key           # noqa: E402


def load_caches(paths: list[str]) -> dict:
    merged: dict = {}
    for p in paths:
        f = REPO / p
        if not f.exists():
            continue
        merged.update(json.loads(f.read_text()))
    return merged


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Derive pairing gaps from cached person-year scores. Free.")
    ap.add_argument("--pairings", default="data/roster100/run/pairing_scores.json",
                    help="supplies the pairing GRAPH; its gaps are ignored")
    ap.add_argument("--cache", action="append", default=None)
    ap.add_argument("--families", default="fable,astra")
    ap.add_argument("--out", default="data/roster100/run/pairing_scores_derived.json")
    args = ap.parse_args()

    caches = load_caches(args.cache or [
        "data/roster100/run/person_period_cache.json",
        "data/roster100/run/person_period_cache_astra.json"])
    families = [f.strip() for f in args.families.split(",") if f.strip()]
    graph = require(REPO, args.pairings)

    out, tax = [], Counter()
    for p in graph["pairings"]:
        per = str(p.get("period") or "")
        per_family: dict[str, float] = {}
        missing: list[str] = []
        for fam in families:
            mk = caches.get(cache_key(p.get("male_qid", ""), per, fam))
            fk = caches.get(cache_key(p.get("female_qid", ""), per, fam))
            if mk is None or fk is None:
                missing.append(f"{fam}:uncached")
                continue
            if not (mk.get("judged") and fk.get("judged")):
                who = mk if not mk.get("judged") else fk
                missing.append(f"{fam}:{who.get('cannot_judge_reason') or 'unjudged'}")
                continue
            per_family[fam] = float(fk["score"]) - float(mk["score"])
        gap = sum(per_family.values()) / len(per_family) if per_family else None
        if gap is None:
            tax[missing[0] if missing else "no_family"] += 1
        out.append({**{k: p.get(k) for k in
                       ("pairing_id", "domain", "period", "work",
                        "male", "female", "male_qid", "female_qid")},
                    "gap": gap, "judges": per_family,
                    "centrality": p.get("centrality"),
                    "uncovered": missing if gap is None else []})

    covered = sum(1 for r in out if r["gap"] is not None)
    art = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "derived_from": "cached person-year scores; no model calls",
        "contract": next(iter(caches.values()))["contract"] if caches else {},
        "pairing_graph": args.pairings,
        "attempted": len(out), "succeeded": covered,
        "unjudged": len(out) - covered, "failed": 0,
        "error_taxonomy": {}, "unjudged_taxonomy": dict(tax),
        "budgets": {}, "pairings": out, "failures": [],
    }
    dest = REPO / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(art, indent=2))
    print(f"{len(out)} pairings; {covered} derived from cache, "
          f"{len(out)-covered} uncovered")
    if tax:
        print(f"  why uncovered: {dict(tax)}")
    print(f"cache entries used: {len(caches)}")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
