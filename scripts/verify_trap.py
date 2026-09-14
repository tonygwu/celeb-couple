#!/usr/bin/env python3
"""Do the structural claims in docs/THE-TRAP.md still hold?

THE-TRAP.md is the capstone finding. It states three things as absolute, with
no exceptions:

  1. Every SHAPE-COMPARABLE jointly covered pairing has a gap of exactly 0.0.
  2. Every non-zero gap is shape-mismatched.
  3. Men in the corpus hold zero ranked observations.

Those are the claims a reader will act on, and every one of them is derivable.
Nothing checked them. The audit built tonight cross-checks numbers typed into
prose; these are structural claims about the corpus, and a number-matcher
cannot see them. Tonight three of the capstone's tables had already drifted.

Each claim can stop being true for a GOOD reason -- a new ranked source
covering a man would break claim 3 and would be the best news this project
could get. That is exactly why it must fail loudly rather than sit in a
document nobody re-derives.

Read-only. Spends no model quota.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from packages.llmkit.artifacts import require  # noqa: E402


def gaps(joint: dict, rows: dict) -> list[dict]:
    """Signed gaps for every jointly covered pairing-period.

    `a_src`/`b_src` name the period an estimate was actually made for, which
    differs from the pairing period under bounded nearby reuse. Using the
    pairing period would silently miss the reused estimate and drop the row.
    """
    out = []
    for p in joint["jointly_covered"]:
        a = rows.get((p["a"], p.get("a_src") or p["period"]))
        b = rows.get((p["b"], p.get("b_src") or p["period"]))
        if not (a and b):
            out.append({**p, "gap": None, "resolved": False})
            continue
        out.append({**p, "resolved": True,
                    "a_estimate": a["estimate"], "b_estimate": b["estimate"],
                    "a_shape": a["shape"], "b_shape": b["shape"],
                    "gap": round(a["estimate"] - b["estimate"], 6)})
    return out


def check(joint: dict, shape_conf: dict, gsc: dict) -> list[dict]:
    rows = {(r["person"], r["period"]): r for r in shape_conf["rows"]}
    g = gaps(joint, rows)
    resolved = [x for x in g if x["resolved"]]
    results = []

    comparable = [x for x in resolved if x["comparability"] == "comparable"]
    bad = [x for x in comparable if x["gap"] != 0.0]
    results.append({
        "claim": "every shape-comparable pairing has a gap of exactly 0.0",
        "holds": not bad, "checked": len(comparable),
        "exceptions": [f"{x['a']} vs {x['b']} {x['period']}: gap {x['gap']}"
                       for x in bad],
        "if_broken": ("A comparable pairing with a non-zero gap is the first "
                      "real signal this project has produced. Read it before "
                      "changing anything."),
    })

    nonzero = [x for x in resolved if x["gap"] not in (None, 0.0)]
    bad2 = [x for x in nonzero if x["comparability"] != "shape_mismatched"]
    results.append({
        "claim": "every non-zero gap is shape-mismatched",
        "holds": not bad2, "checked": len(nonzero),
        "exceptions": [f"{x['a']} vs {x['b']} {x['period']}: gap {x['gap']}, "
                       f"comparability {x['comparability']}" for x in bad2],
        "if_broken": ("Same as above: a non-zero gap that is NOT explained by "
                      "evidence format is the thing the board needs."),
    })

    male_ranked = (gsc.get("ranked_observations") or {}).get("male")
    results.append({
        "claim": "men hold zero ranked observations",
        "holds": male_ranked == 0, "checked": 1,
        "exceptions": ([] if male_ranked == 0
                       else [f"men now hold {male_ranked} ranked observations"]),
        "if_broken": ("The gender-aligned confound is the project's most "
                      "consequential finding. If men now carry ranked "
                      "evidence, re-run gender_shape_confound.py and rewrite "
                      "the confound section of docs/THE-TRAP.md."),
    })
    return results


def main() -> int:
    ap = argparse.ArgumentParser(
        description=("Re-derive the structural claims in docs/THE-TRAP.md from "
                     "the artifacts. Read-only; spends no quota."))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    joint = require(REPO, "data/pilot/run/joint_with_nearby.json")
    shape_conf = require(REPO, "data/pilot/run/shape_confound.json")
    gsc = require(REPO, "data/pilot/run/gender_shape_confound.json")

    results = check(joint, shape_conf, gsc)
    broken = [r for r in results if not r["holds"]]

    if args.json:
        print(json.dumps({"results": results, "all_hold": not broken}, indent=2))
    else:
        for r in results:
            mark = "HOLDS " if r["holds"] else "BROKEN"
            print(f"{mark}  {r['claim']}  (checked {r['checked']})")
            for x in r["exceptions"]:
                print(f"         ! {x}")
            if not r["holds"]:
                print(f"         -> {r['if_broken']}")
        if not broken:
            print("\ndocs/THE-TRAP.md's structural claims all re-derive from "
                  "the artifacts.")
        else:
            print(f"\n{len(broken)} claim(s) in docs/THE-TRAP.md no longer "
                  f"hold. This may be good news; read the exceptions.")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
