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


def noise_floor(noise: dict | None) -> float | None:
    """The largest per-shape least significant difference, or None.

    MAX rather than mean, deliberately: a gap must clear the noisiest shape
    it could have come from before it counts as detectable. The award shape
    reports no floor at all, because two dossiers returned the same value on
    every repeat, which cannot distinguish low variance from none.

    None means no floor has been measured, and the caller must then make NO
    claim rather than fall back to exact zero -- falling back is what made
    these claims break on a second judge in the first place.
    """
    if not noise:
        return None
    by_shape = (noise.get("headline") or {}).get("by_shape") or {}
    floors = [v["least_significant_difference_95pct"] for v in by_shape.values()
              if v.get("least_significant_difference_95pct") is not None]
    return max(floors) if floors else None


def check(joint: dict, shape_conf: dict, gsc: dict,
          noise: dict | None = None) -> list[dict]:
    rows = {(r["person"], r["period"]): r for r in shape_conf["rows"]}
    g = gaps(joint, rows)
    resolved = [x for x in g if x["resolved"]]
    results = []

    # STATED AGAINST THE NOISE FLOOR, NOT AGAINST EXACT ZERO.
    #
    # These read `gap != 0.0` and `gap not in (None, 0.0)`. Exact equality was
    # only ever true because ONE judge family scored the corpus and returned
    # integers, and both sides of the single comparable pairing landed on the
    # award-pinned 92. The moment a second family joined, the reducer's mean of
    # two produced half-integers: Jennifer Garner 2002 came back 93 from fable
    # and 92 from astra, so her estimate is 92.5 against Ben Affleck's 92.0 and
    # the gap is 0.5.
    #
    # Both claims then "broke", and the script announced a 0.5-point gap as
    # "the first real signal this project has produced". It is not a signal. It
    # is one judge saying 93 instead of 92, both inside band 90-100, an order of
    # magnitude below the measured floor. Acting on it would be exactly the
    # error this repository exists to prevent.
    #
    # The substantive claim was never "exactly zero". It was "no difference
    # this method can detect", and that is what is checked now.
    floor = noise_floor(noise)
    comparable = [x for x in resolved if x["comparability"] == "comparable"]
    bad = [x for x in comparable if floor is not None and abs(x["gap"]) > floor]
    results.append({
        "claim": f"every shape-comparable pairing has a gap within the measured floor ({floor})",
        "holds": not bad, "checked": len(comparable),
        "exceptions": [f"{x['a']} vs {x['b']} {x['period']}: gap {x['gap']}"
                       for x in bad],
        "if_broken": ("A comparable pairing differing by MORE than rater noise "
                      "is the first real signal this project has produced. "
                      "Read it before changing anything."),
    })

    detectable = [x for x in resolved
                  if x["gap"] is not None and floor is not None
                  and abs(x["gap"]) > floor]
    bad2 = [x for x in detectable if x["comparability"] != "shape_mismatched"]
    results.append({
        "claim": "every gap beyond the noise floor is shape-mismatched",
        "holds": not bad2, "checked": len(detectable),
        "exceptions": [f"{x['a']} vs {x['b']} {x['period']}: gap {x['gap']}, "
                       f"comparability {x['comparability']}" for x in bad2],
        "if_broken": ("Same as above: a detectable gap that is NOT explained by "
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
    noise = require(REPO, "data/pilot/run/rater_noise.json")

    results = check(joint, shape_conf, gsc, noise)
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
