"""The escalation rule lives in exactly one place.

`scripts/score_evidenced.py` computed `needs_adjudication` itself, as
`bool(gapj and gapj > 10)` -- a hardcoded threshold duplicating
`packages.schema.records.reduce_judges`. The artifact's flag and the library's
flag could therefore disagree, and would have: changing the rule in the library
would not have changed a single stored record, because the script never called
it. Found 2026-09-15 while switching escalation from a gap to a band.

This is the same defect shape the repo has paid for before -- a User-Agent
defined twice, a name predicate defined twice -- so it is asserted as a class.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

#: Where the rule is allowed to live.
_HOME = REPO / "packages/schema/records.py"


def _sources() -> list[Path]:
    out = []
    for d in ("scripts", "modules", "packages"):
        out.extend(p for p in (REPO / d).rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(out)


def test_nothing_outside_records_decides_escalation_for_itself():
    offenders = []
    for p in _sources():
        if p == _HOME:
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            # An ASSIGNMENT to needs_adjudication from anything but the reducer.
            m = re.search(r'["\']?needs_adjudication["\']?\s*[:=]\s*(.+)', line)
            if not m:
                continue
            rhs = m.group(1)
            if "reduce_judges" in rhs or "needs_adj" in rhs or "needs_adjudication" in rhs:
                continue
            offenders.append(f"{p.relative_to(REPO)}:{i}: {line.strip()}")
    assert not offenders, (
        "these set needs_adjudication without going through reduce_judges:\n  "
        + "\n  ".join(offenders)
        + "\nThe rule belongs in packages/schema/records.py alone; a second copy "
          "drifts silently from the first.")


#: A two-sided range check -- `-10 <= gap <= 10` -- is a schema bound, not an
#: escalation decision. The first version of the guard below flagged one in
#: modules/pairing/judge.py, which validates that a returned gap is inside the
#: scale at all. Excluded by SHAPE rather than by filename, so a real one-sided
#: threshold in that same file is still caught.
_RANGE_CHECK = re.compile(r"[-\d.]+\s*<=?\s*gap\w*\s*<=?\s*[-\d.]+")


def test_no_bare_numeric_threshold_is_compared_against_a_judge_gap():
    """Catches the specific shape that shipped: `gap > 10`."""
    offenders = []
    pat = re.compile(r"gap\w*\s*[<>]=?\s*\d")
    for p in _sources():
        if p == _HOME:
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if line.lstrip().startswith("#") or _RANGE_CHECK.search(line):
                continue
            if pat.search(line):
                offenders.append(f"{p.relative_to(REPO)}:{i}: {line.strip()}")
    assert not offenders, "judge gap compared to a literal:\n  " + "\n  ".join(offenders)


def test_the_range_check_exclusion_does_not_hide_a_real_threshold():
    # A guard with an exemption needs the exemption tested, or it becomes a way
    # to smuggle the defect back in.
    assert _RANGE_CHECK.search("if not -10 <= gap <= 10:")
    assert not _RANGE_CHECK.search("needs_adjudication = gap > 10")
    assert not _RANGE_CHECK.search("if gapj and gapj > 10:")


def test_the_reducer_is_actually_reachable_from_the_scoring_script():
    # A rule with one home is only safe if the home is CALLED. This is the
    # sibling failure: refuse_mixed_contracts was correct and uncalled for weeks.
    src = (REPO / "scripts/score_evidenced.py").read_text()
    assert "reduce_judges(" in src, "score_evidenced.py no longer calls the reducer"
    assert "from packages.schema.records import" in src
