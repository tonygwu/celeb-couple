#!/usr/bin/env python3
"""Run the automated grounding checks and render a human review sheet.

The machine half checks that a rationale does not assert more than its evidence
carries. The human half is the point: the sheet puts each claim beside the
observations it cites so a person can judge whether it is a fair reading.
Spends no model quota.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from modules.consensus.grounding import AUTOMATED_CHECKS, check_rationale  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default="data/pilot/run/evidenced_scores.json")
    ap.add_argument("--observations", default="data/pilot/observations/observations.json")
    ap.add_argument("--out-json", default="data/pilot/run/grounding_audit.json")
    ap.add_argument("--out-md", default="docs/GROUNDING-AUDIT.md")
    args = ap.parse_args()

    scores = json.loads((REPO / args.scores).read_text())
    obs_blob = json.loads((REPO / args.observations).read_text())
    editions = {e["list_edition_id"]: e for e in obs_blob["editions"]}
    by_pp: dict[tuple[str, str], list[dict]] = {}
    for o in obs_blob["observations"]:
        ed = editions.get(o["list_edition_id"], {})
        by_pp.setdefault((o["person_id"], o["concerns_period"]), []).append({
            "observation_id": o["observation_id"],
            "evidence_type": o["evidence_type"],
            "publisher": ed.get("publisher"),
            "concerns_period": o["concerns_period"],
            "rank": o["observed"].get("rank"),
            "list_length": o["observed"].get("list_length"),
            "original_source": o["lineage"]["original_source"],
            "excerpt": o.get("excerpt", ""),
        })

    checks = []
    for rec in scores["person_periods"]:
        if rec["estimate"] is None:
            continue
        observations = by_pp.get((rec["person_id"], rec["period"]), [])
        for judge, rationale in (rec.get("rationales") or {}).items():
            cited = [o["observation_id"] for o in observations if o["observation_id"] in rationale]
            checks.append(check_rationale(
                estimate_id=f"{rec['person_id']}_{rec['period']}_{judge}",
                person=f"{rec['person']} [{judge}]", period=rec["period"],
                estimate=rec["judges"].get(judge, rec["estimate"]),
                rationale=rationale, cited_ids=cited,
                dossier_ids=[o["observation_id"] for o in observations],
                observations=observations))

    failed = [c for c in checks if not c.passed]
    warned = [c for c in checks if c.passed and c.warnings]
    payload = {
        "automated_checks": list(AUTOMATED_CHECKS),
        "counts": {"rationales": len(checks), "passed_automated": len(checks) - len(failed),
                   "failed_automated": len(failed), "warned": len(warned),
                   "needing_human_read": sum(1 for c in checks if c.needs_human_read)},
        "limitation": (
            "These checks prove a rationale does not assert MORE than its evidence "
            "carries. They do not prove it is a fair reading. Only the human sheet "
            "can establish that."
        ),
        "checks": [c.as_dict() for c in checks],
    }
    (REPO / args.out_json).write_text(json.dumps(payload, indent=2))

    L = ["# Grounding audit — human review sheet", "",
         "Each row puts a rationale beside the observations it cites. Read the "
         "evidence, then the claim, and mark whether the claim is a fair reading.",
         "",
         f"Automated: {payload['counts']['passed_automated']} of "
         f"{payload['counts']['rationales']} rationales passed; "
         f"{payload['counts']['failed_automated']} failed; "
         f"{payload['counts']['warned']} warned.", "",
         f"**{payload['limitation']}**", ""]
    for c in checks:
        L += [f"## {c.person} — {c.period} — estimate {c.estimate}", ""]
        if c.failures:
            L += ["**AUTOMATED FAILURES**"] + [f"- {f}" for f in c.failures] + [""]
        if c.warnings:
            L += ["**Flags**"] + [f"- {w}" for w in c.warnings] + [""]
        L += ["**Evidence the dossier contained**"]
        L += [f"- {e}" for e in c.evidence_summary] or ["- (none)"]
        L += ["", "**The rationale**", "", f"> {c.rationale}", "",
              "**Fair reading?**  [ ] yes  [ ] no  [ ] unsure — notes:", "", "---", ""]
    (REPO / args.out_md).write_text("\n".join(L) + "\n")

    print(json.dumps(payload["counts"], indent=2))
    for c in failed:
        print(f"  FAIL {c.person} {c.period}: {c.failures}")
    print(f"wrote {REPO / args.out_json}\nwrote {REPO / args.out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
