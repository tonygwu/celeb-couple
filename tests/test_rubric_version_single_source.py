"""A rubric version string is typed in exactly one place.

docs/CONTRACT-BUMP.md: "A changed contract with an unchanged version string is
the worst outcome, because the artifacts then disagree about which rubric they
used." The standing version was typed as a literal in five scripts, so a bump
meant five hand-edits and one of them getting missed was a matter of time.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.llmkit.contract import (MENTIONS_RUBRIC_VERSION,  # noqa: E402
                                      ROMANCE_RUBRIC_VERSION,
                                      STANDING_RUBRIC_VERSION)

#: Where the constants are allowed to be spelled out.
_HOME = REPO / "packages/llmkit/contract.py"

#: A rubric version literal looks like `standing-rubric-2.1`. The pattern is
#: deliberately about SHAPE rather than about the three known names, because
#: a fourth rubric must be caught too -- this repo has been bitten twice by
#: code that enumerated a set which later grew.
_LITERAL = re.compile(r'["\'](?:[a-z]+-)*rubric-\d+\.\d+["\']|["\'](?:mentions|romance)-\d+\.\d+["\']')


def _tracked_python() -> list[Path]:
    out = []
    for d in ("scripts", "modules", "packages"):
        out.extend(sorted((REPO / d).rglob("*.py")))
    return [p for p in out if "__pycache__" not in p.parts]


def test_no_script_types_a_rubric_version_literal():
    offenders = []
    for p in _tracked_python():
        if p == _HOME:
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if line.lstrip().startswith("#"):
                continue
            # `schema_version` is the judge's OUTPUT shape, a different field
            # that is checked against the schema's own const. It is not the
            # rubric version and does not move when the rubric does.
            if "schema_version" in line:
                continue
            if _LITERAL.search(line):
                offenders.append(f"{p.relative_to(REPO)}:{i}: {line.strip()}")
    assert not offenders, (
        "rubric version typed outside packages/llmkit/contract.py:\n  "
        + "\n  ".join(offenders)
        + "\nImport the constant instead, or a bump will miss this call site."
    )


def test_the_constants_name_the_rubrics_that_exist():
    # A constant for a rubric directory that is gone would bump nothing.
    dirs = {d.name for d in (REPO / "rubrics").iterdir() if d.is_dir()}
    assert dirs == {"standing", "mentions", "romance"}, dirs
    assert STANDING_RUBRIC_VERSION.startswith("standing-rubric-")
    assert MENTIONS_RUBRIC_VERSION.startswith("mentions-")
    assert ROMANCE_RUBRIC_VERSION.startswith("romance-")


def test_the_bump_actually_happened():
    # The bytes of the standing and mentions rubrics changed on 2026-09-14, so
    # their versions had to move. Romance's bytes did not, so its must not.
    assert STANDING_RUBRIC_VERSION == "standing-rubric-2.1"
    assert MENTIONS_RUBRIC_VERSION == "mentions-1.1"
    assert ROMANCE_RUBRIC_VERSION == "romance-1.0"
