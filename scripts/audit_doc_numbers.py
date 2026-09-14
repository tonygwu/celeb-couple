#!/usr/bin/env python3
"""Cross-check measured numbers typed into prose against the artifacts.

Three times in one night a published number went stale: the shape-confound
percentage, the count of distinct estimate values, and the observation total.
Each time the document still read plausibly. `tests/test_doc_claims.py` guards
two numbers in README.md by name, which caught all three -- but only in that
one file, and only for those two quantities. The same 42% sat wrong in two
backlog files the whole time because nothing looked there.

This walks every tracked Markdown file, finds each registered quantity by its
own pattern, and compares what the prose says to what the artifact says.

It is deliberately NOT a general number scanner. A scanner that guesses which
integers in a document are measurements produces false alarms, and a guard that
cries wolf gets bypassed. Every quantity here is declared: where it lives, how
it is formatted, and the exact phrasing that means it. A quantity nobody
declared is not checked, and adding one is three lines.

Generated docs are skipped: re-running their generator is the fix, and
`tests/test_report_prose.py` already asserts M0-REPORT matches its inputs.

Exit 0 when every occurrence agrees, 1 when any disagrees, 2 when an artifact
a rule needs is missing.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parent.parent

#: Documents written by a generator. Editing them by hand is the bug; the fix
#: is to re-run the generator, so a mismatch here is not actionable prose.
GENERATED = {"docs/M0-REPORT.md", "docs/GROUNDING-AUDIT.md"}


#: Documents measuring the 100-name roster corpus, not the 14-person pilot.
#: Their denominators are genuinely different, so a pilot rule that matched
#: here would report a false mismatch -- and one false alarm is all it takes
#: for the next agent to stop believing this script.
ROSTER_SCALE = {"docs/SCALING.md", "docs/REACHABLE-PRODUCTS.md",
                "docs/SOURCE-HUNT.md", "docs/BACKLOG-roster.md"}


def flex(pattern: str) -> str:
    """Let a pattern span a line wrap.

    Found the hard way: `docs/BACKLOG-roster.md` had "explains 42% of the\n
    estimate" and the first version of this script reported it clean. Prose
    wraps wherever the author's editor wrapped it, so a literal space in a
    pattern has to mean "any run of whitespace".
    """
    return r"\s+".join(pattern.split(" "))


@dataclass(frozen=True)
class Rule:
    name: str
    artifact: str
    #: Pulls the authoritative value out of the loaded artifact. Raises
    #: KeyError if the artifact no longer carries it, which is a loud failure
    #: rather than a silently skipped check.
    extract: Callable[[dict], Any]
    #: Renders it the way prose writes it.
    render: Callable[[Any], str]
    #: Must capture the written number in group 1.
    pattern: str
    why: str
    #: Documents this rule must not be applied to. Empty means every document.
    skip: frozenset = frozenset()


RULES: tuple[Rule, ...] = (
    Rule(
        name="shape_confound_pct",
        artifact="data/pilot/run/shape_confound.json",
        # The documents lead with omega-squared now: eta is biased upward and
        # was overstating this by about eight points.
        extract=lambda d: d["omega_squared_shape_explains"],
        render=lambda v: str(round(v * 100)),
        pattern=r"(\d+)% of the (?:estimate|variance)",
        why="how much of an estimate is evidence format rather than the person",
    ),
    Rule(
        name="total_observations",
        artifact="data/pilot/run/evidence_density.json",
        extract=lambda d: d["observations"],
        render=str,
        pattern=r"(\d+) observations over \d+ of \d+ people",
        why="the size of the PILOT evidence corpus",
        skip=frozenset(ROSTER_SCALE),
    ),
    Rule(
        name="gender_offset",
        artifact="data/pilot/run/gender_shape_confound.json",
        extract=lambda d: d["mean_offset_male_minus_female"],
        render=lambda v: f"{v:g}",
        pattern=r"male mean sits (\d+(?:\.\d+)?) points above",
        why="the gender-aligned confound, the project's most consequential finding",
    ),
    Rule(
        name="female_ranked_observations",
        artifact="data/pilot/run/gender_shape_confound.json",
        extract=lambda d: d["ranked_observations"]["female"],
        render=str,
        pattern=r"[Ww]omen hold (\d+)",
        why="one half of the ranked-observation imbalance",
    ),
    # --- roster-scale quantities -------------------------------------------
    # These read a different corpus than the pilot rules above. Their patterns
    # all name "roster", "scorable relationship" or "of 239", so they cannot
    # match a pilot document by accident and need no skip list.
    Rule(
        name="roster_observations",
        artifact="data/roster100/run/reachable.json",
        extract=lambda d: d["corpus"]["observations"],
        render=str,
        pattern=r"(\d+) observations over \d+ of \d+ roster people",
        why="the size of the 100-name roster corpus",
    ),
    Rule(
        name="roster_people_with_evidence",
        artifact="data/roster100/run/reachable.json",
        extract=lambda d: d["corpus"]["roster_people_with_evidence"],
        render=str,
        pattern=r"\d+ observations over (\d+) of \d+ roster people",
        why="how many of the 100 roster names carry any evidence at all",
    ),
    Rule(
        name="scorable_episodes",
        artifact="data/roster100/run/reachable.json",
        extract=lambda d: d["corpus"]["scorable_episodes"],
        render=str,
        pattern=r"(\d+) scorable relationship episodes",
        why="the denominator every reachable-product option is measured against",
    ),
    Rule(
        name="coverage_saturation",
        artifact="data/roster100/run/source_requirement.json",
        # The curve flattens: 22 covered episodes at 100 names/year and still 22
        # at 400. The ceiling is the maximum median, not the last rung.
        extract=lambda d: max(r["median_covered"] for r in d["ladder"]),
        render=str,
        pattern=r"about (\d+) of 239 episodes",
        why="the ceiling this design reaches even with a perfect source",
    ),
    Rule(
        name="pilot_ordered_rank_observations",
        artifact="data/pilot/run/evidence_density.json",
        extract=lambda d: d["observation_shapes"]["ordered_rank"],
        render=str,
        pattern=r"(\d+) `ordered_rank` observations for the pilot",
        why="how much rank-shaped evidence the pilot corpus holds",
    ),
    Rule(
        name="partners_total",
        artifact="data/pilot/records/partner_eligibility.json",
        extract=lambda d: d["partners"],
        render=str,
        pattern=r"Of (\d+)\s*partners",
        why="the denominator for how much of the board is reachable",
    ),
    Rule(
        name="ranked_lsd",
        artifact="data/pilot/run/rater_noise.json",
        extract=lambda d: (d["headline"]["by_shape"]["ranked"]
                           ["least_significant_difference_95pct"]),
        render=lambda v: f"{v:g}",
        # The alternation is narrow on purpose. docs/THE-TRAP.md deliberately
        # quotes the OLD pooled figure ("the published least significant
        # difference of 1.2 points was too small"), and a looser pattern would
        # report that correct historical sentence as stale.
        pattern=(r"(?:least significant difference (?:at|of) about"
                 r"|LSD of"
                 r"|rank-shaped LSD is \*\*)\s*(\d+(?:\.\d+)?)"),
        why="the noise floor a gap has to clear to mean anything",
    ),
    Rule(
        name="real_distinct_values",
        artifact="data/pilot/run/evidence_density.json",
        extract=lambda d: d["real_estimate_spread"]["distinct_values"],
        render=str,
        pattern=r"produces (\d+) across a range",
        why="whether the pilot corpus can tell people apart at all",
        skip=frozenset(ROSTER_SCALE),
    ),
)


def find_mismatches(rule: "Rule", expected: str,
                    docs: dict[str, str]) -> list[dict]:
    """Every place `docs` states this quantity as something other than `expected`.

    Split out from `audit` so it can be tested without the artifacts, which
    live under a gitignored `data/`. A test that reads `data/` passes in the
    clone that produced it and fails in every fresh one, which this repo has
    already paid for once.
    """
    out: list[dict] = []
    for path, text in docs.items():
        if path in rule.skip:
            continue
        for m in re.finditer(flex(rule.pattern), text):
            if m.group(1) != expected:
                out.append({
                    "rule": rule.name, "file": path,
                    "line": text[: m.start()].count("\n") + 1,
                    "written": m.group(1), "artifact_says": expected,
                    "quantity": rule.why, "source": rule.artifact,
                    "excerpt": m.group(0),
                })
    return out


def tracked_markdown(repo: Path) -> list[str]:
    out = subprocess.run(["git", "ls-files", "*.md"], cwd=repo,
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.split() if p not in GENERATED]


def audit(repo: Path) -> tuple[list[dict], list[str]]:
    """Return (mismatches, missing_artifacts)."""
    docs = {p: (repo / p).read_text() for p in tracked_markdown(repo)}
    mismatches: list[dict] = []
    missing: list[str] = []

    for rule in RULES:
        f = repo / rule.artifact
        if not f.exists():
            missing.append(f"{rule.name}: {rule.artifact}")
            continue
        expected = rule.render(rule.extract(json.loads(f.read_text())))
        mismatches.extend(find_mismatches(rule, expected, docs))
    return mismatches, missing


def main() -> int:
    ap = argparse.ArgumentParser(
        description=("Cross-check measured numbers typed into tracked Markdown "
                     "against the run artifacts. Reads only; spends no quota."))
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    mismatches, missing = audit(REPO)

    if args.json:
        print(json.dumps({"mismatches": mismatches, "missing_artifacts": missing,
                          "rules_checked": len(RULES)}, indent=2))
    else:
        for w in missing:
            print(f"MISSING ARTIFACT  {w}")
        for m in mismatches:
            print(f"STALE  {m['file']}:{m['line']}  \"{m['excerpt']}\"")
            print(f"       {m['source']} says {m['artifact_says']} "
                  f"-- {m['quantity']}")
        if not mismatches and not missing:
            print(f"{len(RULES)} quantities checked across "
                  f"{len(tracked_markdown(REPO))} tracked documents; "
                  f"every occurrence agrees with its artifact.")

    if missing:
        return 2
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
