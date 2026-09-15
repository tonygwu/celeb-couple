#!/usr/bin/env python3
"""Judge each pairing once and return the GAP. SPENDS MODEL QUOTA.

One call covers one pairing. The judge compares two people at one date in a
single act of judgment, which is the whole point: v3 scored each person
separately and subtracted, and two absolute judgments made in different calls
drift against each other. Labelling that drift is the only reason
`modules/analytics/comparability.py` exists. A relative judgment has no drift to
label.

Plan v4 sections 4 and 5.
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

from packages.llmkit.accounts import (resolve_account,                  # noqa: E402
                                      resolve_codex_home)
from packages.llmkit.artifacts import require                           # noqa: E402
from packages.llmkit.budget import Budget, BudgetExhausted              # noqa: E402
from packages.llmkit.contract import PAIRING_RUBRIC_VERSION, load_contract  # noqa: E402
from packages.llmkit.judges import ClaudeJudge, CodexJudge, JudgeError  # noqa: E402
from packages.llmkit.outputs import archive_previous                    # noqa: E402
from modules.pairing.judge import ParseError, parse_pairing_verdict     # noqa: E402

RUBRIC = REPO / "rubrics/pairing/PAIRING.md"
SCHEMA = REPO / "rubrics/pairing/pairing.schema.json"


def build_prompt(p: dict, rubric: str, schema: str) -> str:
    if p["domain"] == "on_screen":
        what = (f"A film: **{p['work']}**, released {p['period']}.\n"
                f"Judge them as they were presented IN THAT FILM.")
    else:
        span = p.get("period_span") or [p["period"]]
        when = span[0] if span[0] == span[-1] else f"{span[0]} to {span[-1]}"
        what = (f"A real-life relationship, {when}.\n"
                f"Judge them as they were presented during that period. "
                f"`centrality` is 1.0 for a real-life relationship.")
    return (
        f"{rubric}\n\n"
        f"## The output schema\n\n```json\n{schema}\n```\n\n"
        f"## The pairing\n\n"
        f"`pairing_id`: {p['pairing_id']}\n"
        f"Woman: **{p['female']}**\n"
        f"Man: **{p['male']}**\n"
        f"{what}\n\n"
        f"Return the JSON object and nothing else. `gap` is "
        f"({p['female']}) minus ({p['male']})."
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Judge pairings and return the gap. SPENDS MODEL QUOTA.")
    ap.add_argument("--slice", default="data/roster100/run/m1_slice.json")
    ap.add_argument("--judges", default="fable")
    ap.add_argument("--account", default=None,
                    help="Claude config dir, or `default` for the account bare "
                         "`claude` uses. No default: run `quotapick status` first.")
    ap.add_argument("--model", default="claude-fable-5-1")
    ap.add_argument("--astra-account", default=None,
                    help="CODEX_HOME for the astra judge. No default: an "
                         "inherited CODEX_HOME is a hidden choice.")
    ap.add_argument("--max-calls", type=int, default=150)
    ap.add_argument("--out", default="data/roster100/run/pairing_scores.json")
    ap.add_argument("--raw", default="data/roster100/run/raw_pairings")
    ap.add_argument("--tag", default="", help="suffix for raw files, for repeat runs")
    ap.add_argument("--limit", type=int, default=None, help="judge only the first N")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    sl = require(REPO, args.slice)
    pairings = sl["pairings"][:args.limit] if args.limit else sl["pairings"]
    names = [n.strip() for n in args.judges.split(",") if n.strip()]

    print(f"{len(pairings)} pairings x {len(names)} judge(s) = "
          f"{len(pairings) * len(names)} model calls, cap {args.max_calls} per judge")
    if args.dry_run:
        for p in pairings[:5]:
            print(f"  {p['domain']:<10} {p['period']}  {p['female']} / {p['male']}"
                  f"  {p['work'] or ''}")
        print("dry run; nothing spent")
        return 0

    contract = load_contract(RUBRIC, SCHEMA, PAIRING_RUBRIC_VERSION)
    rubric, schema = RUBRIC.read_text(), SCHEMA.read_text()
    raw_dir = REPO / args.raw
    raw_dir.mkdir(parents=True, exist_ok=True)

    judges = []
    for n in names:
        if n == "astra":
            judges.append((n, CodexJudge(
                "astra", "gpt-6-astra", effort="high",
                config_dir=resolve_codex_home(args.astra_account))))
        else:
            judges.append((n, ClaudeJudge(n, args.model,
                                          config_dir=resolve_account(args.account))))
    budgets = {n: Budget(max_calls=args.max_calls) for n, _ in judges}

    records, failures = [], []
    taxonomy: Counter = Counter()
    for i, p in enumerate(pairings, 1):
        per_judge, reasons, cent = {}, {}, {}
        unjudged: dict[str, str] = {}
        for jname, judge in judges:
            try:
                budgets[jname].spend_call(f"{p['pairing_id']} ({jname})")
            except BudgetExhausted as exc:
                print(f"  HALT {jname}: {exc}")
                break
            try:
                res = judge(build_prompt(p, rubric, schema))
            except JudgeError as exc:
                taxonomy[exc.args[0]] += 1
                failures.append({"pairing_id": p["pairing_id"], "judge": jname,
                                 "error": exc.args[0], "detail": str(exc)})
                continue
            suffix = f"__{jname}{args.tag}.txt"
            (raw_dir / f"{p['pairing_id']}{suffix}").write_text(res.text)
            try:
                v = parse_pairing_verdict(res.text, p["pairing_id"])
            except ParseError as exc:
                taxonomy["schema"] += 1
                failures.append({"pairing_id": p["pairing_id"], "judge": jname,
                                 "error": "schema", "detail": str(exc)})
                continue
            if v.judged:
                per_judge[jname] = v.gap
                reasons[jname] = v.reasoning
                cent[jname] = 1.0 if p["domain"] == "real_life" else v.centrality
            else:
                # RECORDED, not dropped. A verdict of "I cannot judge this" is
                # neither a success nor a failure, and the first run reported
                # `attempted 131, succeeded 59, failed 0`, leaving 72 pairings
                # unaccounted for anywhere in the artifact. 49 of them were
                # `person_unknown` because the prompt named nobody.
                unjudged[jname] = v.cannot_judge_reason or "unstated"
        gap = sum(per_judge.values()) / len(per_judge) if per_judge else None
        c = ([x for x in cent.values() if x is not None] or [None])[0]
        records.append({**{k: p[k] for k in ("pairing_id", "domain", "period",
                                             "work", "male", "female",
                                             "male_qid", "female_qid")},
                        "gap": gap, "judges": per_judge, "centrality": c,
                        "unjudged": unjudged, "reasonings": reasons})
        if gap is not None:
            print(f"  [{i}/{len(pairings)}] {p['domain']:<10} {p['period']}  "
                  f"{str(p['female'])[:18]:<18} / {str(p['male'])[:18]:<18} "
                  f"gap {gap:+.2f}  C={c}")
        else:
            print(f"  [{i}/{len(pairings)}] {p['domain']:<10} {p['period']}  "
                  f"{str(p['female'])[:18]:<18} / {str(p['male'])[:18]:<18} UNJUDGED")

    out = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract": contract.as_dict(),
        "slice": args.slice,
        # attempted = succeeded + unjudged + failed, and it must ADD UP. A bare
        # completion count made a run that judged 45% of its slice look like a
        # clean success with nothing failing.
        "attempted": len(pairings) * len(judges),
        "succeeded": sum(1 for r in records if r["gap"] is not None),
        "unjudged": sum(1 for r in records if r["gap"] is None),
        "failed": len(failures),
        "error_taxonomy": dict(taxonomy),
        "unjudged_taxonomy": dict(Counter(
            reason for r in records for reason in (r.get("unjudged") or {}).values())),
        "budgets": {n: b.report() for n, b in budgets.items()},
        "pairings": records,
        "failures": failures,
    }
    dest = REPO / args.out
    dest.parent.mkdir(parents=True, exist_ok=True)
    kept = archive_previous(dest)
    if kept is not None:
        print(f"  [archive] previous kept at {kept}")
    dest.write_text(json.dumps(out, indent=2))
    total = out["succeeded"] + out["unjudged"] + out["failed"]
    print(f"\nattempted {out['attempted']}  succeeded {out['succeeded']}  "
          f"unjudged {out['unjudged']}  failed {out['failed']}")
    if out["unjudged_taxonomy"]:
        print(f"  unjudged: {out['unjudged_taxonomy']}")
    if taxonomy:
        print(f"  errors:   {dict(taxonomy)}")
    if total != out["attempted"]:
        print(f"  WARNING: {out['attempted']} attempted but "
              f"{total} accounted for; {out['attempted'] - total} vanished")
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
