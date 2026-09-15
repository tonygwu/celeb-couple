#!/usr/bin/env python3
"""Judge each (person, year) ONCE, film-blind and evidence-anchored, and cache it.

SPENDS MODEL QUOTA, but only for tuples not already in the cache. Re-running
after adding pairings costs only the new tuples.

WHY THIS REPLACES THE PER-PAIRING JUDGMENT (plan v4 amendment, 2026-09-15):

The pairing rubric told the judge which film it was scoring and asked it to
judge "as they were presented IN THAT FILM". Measured consequence: the same
judge gave the same person in the same year 9.0 for one film and 9.5 for
another, and 15 of 57 reused person-years moved MORE than the 0.28 points by
which the two judge families disagree with each other. A judge disagreeing with
itself more than two different models disagree is not signal.

Film-blind fixes it by construction: one score per person-year, reused
everywhere. It also makes the score CACHEABLE, which is what lets the corpus
grow incrementally instead of being re-judged whole.

And it lets the score be EVIDENCE-ANCHORED. 131 dated observations sit in
data/roster100/observations/ -- awards and ranked placements reported by
Wikipedia -- which the per-pairing rubric could not use, because they are facts
about a person in a year and not about a film. Attaching them answers the
weakness plan v4 section 9 names: "the numbers are unfalsifiable".

The cost, stated: the gap is now a SUBTRACTION of two independently judged
scores rather than one relative judgment. Plan v4 section 4 chose the relative
judgment deliberately. What makes the trade acceptable here is that the two
scores no longer come from different CONTEXTS -- neither is anchored to a film.
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

from packages.llmkit.accounts import (resolve_account,                    # noqa: E402
                                      resolve_codex_home)
from packages.llmkit.artifacts import require                             # noqa: E402
from packages.llmkit.budget import Budget, BudgetExhausted                # noqa: E402
from packages.llmkit.contract import PERSON_RUBRIC_VERSION, load_contract  # noqa: E402
from packages.llmkit.judges import ClaudeJudge, CodexJudge, JudgeError    # noqa: E402
from modules.pairing.person import (ParseError, cache_key,                # noqa: E402
                                    parse_person_verdict, person_period_id)

RUBRIC = REPO / "rubrics/person/PERSON.md"
SCHEMA = REPO / "rubrics/person/person.schema.json"
NEARBY = 1          # observations this many years either side count as dated evidence


def needed_tuples(slice_or_scores: dict) -> list[tuple[str, str, str]]:
    """Every (qid, period, display name) the pairings require.

    Deduplicated, which is the whole point: 119 judged pairings need 196
    distinct person-years, not 238 person-slots.
    """
    seen: dict[tuple[str, str], str] = {}
    for p in slice_or_scores.get("pairings", []):
        if p.get("gap") is None and "male_qid" not in p:
            continue
        for q, n in ((p.get("male_qid"), p.get("male")),
                     (p.get("female_qid"), p.get("female"))):
            if q and p.get("period"):
                seen.setdefault((q, str(p["period"])), n or q)
    return sorted((q, per, n) for (q, per), n in seen.items())


def evidence_for(obs: list[dict], qid: str, period: str) -> list[dict]:
    """Dated observations for this person within the nearby-period bound."""
    out = []
    for o in obs:
        if o.get("person_id") != qid:
            continue
        cp = str(o.get("concerns_period") or "")
        if cp.isdigit() and abs(int(cp) - int(period)) <= NEARBY:
            out.append(o)
    return sorted(out, key=lambda o: o.get("observation_id", ""))


def build_prompt(name: str, period: str, ppid: str, ev: list[dict],
                 rubric: str, schema: str) -> str:
    if ev:
        lines = []
        for o in ev:
            obs = o.get("observed") or {}
            detail = (f"rank {obs['rank']} of {obs.get('list_length','?')}"
                      if obs.get("rank") is not None else
                      obs.get("award_name") or o.get("evidence_type", ""))
            lines.append(f"- `{o['observation_id']}` ({o.get('concerns_period')}) "
                         f"{detail} — \"{o.get('excerpt','').strip()}\"")
        block = ("## Dated published observations for this person and year\n\n"
                 + "\n".join(lines) + "\n")
    else:
        block = ("## Dated published observations for this person and year\n\n"
                 "**None supplied.** That is the normal case and is not evidence "
                 "of a low score. Judge from what you know and set "
                 "`evidence_used` to false.\n")
    return (f"{rubric}\n\n## The output schema\n\n```json\n{schema}\n```\n\n"
            f"{block}\n## The judgment\n\n"
            f"`person_period_id`: {ppid}\n"
            f"Person: **{name}**\nYear: **{period}**\n\n"
            f"How conventionally attractive was {name} perceived to be in "
            f"{period}? Return the JSON object and nothing else.")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Judge person-years, film-blind and cached. SPENDS MODEL QUOTA.")
    ap.add_argument("--from-scores", action="append",
                    default=None, help="pairing artifacts whose people to judge")
    ap.add_argument("--judges", default="fable")
    ap.add_argument("--account", default=None)
    ap.add_argument("--astra-account", default=None)
    ap.add_argument("--model", default="claude-fable-5-1")
    ap.add_argument("--observations", default="data/roster100/observations/observations.json")
    ap.add_argument("--cache", default="data/roster100/run/person_period_cache.json")
    ap.add_argument("--raw", default="data/roster100/run/raw_person")
    ap.add_argument("--max-calls", type=int, default=250)
    ap.add_argument("--limit", type=int, default=None,
                    help="judge at most N uncached tuples; the rest stay on the backlog")
    ap.add_argument("--backlog-only", action="store_true",
                    help="print what is uncached and exit without spending")
    args = ap.parse_args()

    sources = args.from_scores or ["data/roster100/run/pairing_scores.json"]
    tuples: dict[tuple[str, str], str] = {}
    for s in sources:
        for q, per, n in needed_tuples(require(REPO, s)):
            tuples.setdefault((q, per), n)
    obs = require(REPO, args.observations)["observations"]

    cache_path = REPO / args.cache
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    names = [j.strip() for j in args.judges.split(",") if j.strip()]

    backlog = [(q, per, tuples[(q, per)], j)
               for (q, per) in sorted(tuples) for j in names
               if cache_key(q, per, j) not in cache]
    with_ev = sum(1 for (q, per) in tuples if evidence_for(obs, q, per))
    print(f"{len(tuples)} person-years needed, {len(names)} judge(s)")
    print(f"  cached already: {len(tuples)*len(names) - len(backlog)}")
    print(f"  BACKLOG:        {len(backlog)}")
    print(f"  with dated published evidence: {with_ev} of {len(tuples)}")
    if args.backlog_only:
        for q, per, n, j in backlog[:20]:
            print(f"    {j:<6} {n} ({per})")
        if len(backlog) > 20:
            print(f"    ... and {len(backlog)-20} more")
        return 0
    if args.limit:
        backlog = backlog[:args.limit]
        print(f"  judging {len(backlog)} this run; the rest stay on the backlog")

    contract = load_contract(RUBRIC, SCHEMA, PERSON_RUBRIC_VERSION)
    rubric, schema = RUBRIC.read_text(), SCHEMA.read_text()
    raw_dir = REPO / args.raw
    raw_dir.mkdir(parents=True, exist_ok=True)

    judges = {}
    for j in names:
        judges[j] = (CodexJudge("astra", "gpt-6-astra", effort="high",
                                config_dir=resolve_codex_home(args.astra_account))
                     if j == "astra" else
                     ClaudeJudge(j, args.model, config_dir=resolve_account(args.account)))
    budgets = {j: Budget(max_calls=args.max_calls) for j in names}
    tax: Counter = Counter()
    done = failed = 0

    for i, (q, per, name, j) in enumerate(backlog, 1):
        ppid = person_period_id(q, per)
        try:
            budgets[j].spend_call(f"{ppid} ({j})")
        except BudgetExhausted as exc:
            print(f"  HALT {j}: {exc}")
            break
        ev = evidence_for(obs, q, per)
        try:
            res = judges[j](build_prompt(name, per, ppid, ev, rubric, schema))
        except JudgeError as exc:
            tax[exc.args[0]] += 1; failed += 1
            print(f"  [{i}/{len(backlog)}] {name} {per} {j}  FAILED {exc.args[0]}")
            continue
        (raw_dir / f"{ppid}__{j}.txt").write_text(res.text)
        try:
            v = parse_person_verdict(res.text, ppid)
        except ParseError as exc:
            tax["schema"] += 1; failed += 1
            print(f"  [{i}/{len(backlog)}] {name} {per} {j}  SCHEMA {exc}")
            continue
        cache[cache_key(q, per, j)] = {
            "person_id": q, "person": name, "period": per, "family": j,
            "judged": v.judged, "score": v.score,
            "evidence_used": v.evidence_used, "evidence_ids": list(v.evidence_ids),
            "evidence_available": [o["observation_id"] for o in ev],
            "reasoning": v.reasoning, "cannot_judge_reason": v.cannot_judge_reason,
            "contract": contract.as_dict(),
        }
        done += 1
        # Written EVERY time, not at the end. A run the machine sleeps through
        # keeps every tuple it paid for; AGENTS.md records why that matters.
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True))
        mark = "ev" if v.evidence_used else "  "
        print(f"  [{i}/{len(backlog)}] {name[:24]:<24} {per} {j:<6} {mark} "
              f"-> {v.score if v.judged else 'UNJUDGED'}")

    print(f"\nattempted {done+failed}  cached {done}  failed {failed}  {dict(tax)}")
    print(f"cache now holds {len(cache)} entries; "
          f"{len(tuples)*len(names) - len(cache)} still on the backlog")
    print(f"wrote {cache_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
