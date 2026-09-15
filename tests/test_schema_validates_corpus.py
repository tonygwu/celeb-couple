"""Every stored judge verdict validates against the schema it was produced under.

This test could not exist before 2026-09-14. `missingness_reason` and `band`
were declared `"type": ["string", "null"]` alongside an `enum` that omitted
null, and JSON Schema keywords are conjunctive, so null failed both fields.
Every SCORED record sets `missingness_reason` to null, so a validator would
have rejected the entire corpus the moment it was introduced -- 52 of 52
measured. That was the landmine filed in docs/BACKLOG.md as W110.

The enums are fixed, so validation is now a gate rather than a trap, and this
is what proves the fix was real rather than cosmetic.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

REPO = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO / "rubrics/standing/estimate.schema.json"

#: Where raw judge verdicts are stored, one JSON object per file. Globbed
#: rather than listed: the stress and repeat directories arrived after the
#: scoring one and would have been missed by a hardcoded list.
_RAW_DIRS = ("data/pilot/run/raw", "data/pilot/run/raw_repeats",
             "data/pilot/stress/raw")


def _schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


def _verdicts() -> list[tuple[str, dict]]:
    out = []
    for d in _RAW_DIRS:
        root = REPO / d
        if not root.is_dir():
            continue
        for f in sorted(root.rglob("*.txt")):
            try:
                obj = json.loads(f.read_text())
            except json.JSONDecodeError:
                continue          # a refusal or a truncated response, not a verdict
            if isinstance(obj, dict) and obj.get("schema_version"):
                out.append((str(f.relative_to(REPO)), obj))
    return out


def test_there_are_verdicts_to_validate():
    # Without this, an empty glob would make every assertion below vacuous --
    # the defect this repo has already paid for once.
    assert len(_verdicts()) >= 40, "raw verdicts missing; the check below proves nothing"


def test_every_stored_verdict_validates():
    v = jsonschema.Draft7Validator(_schema())
    failures = []
    for name, obj in _verdicts():
        for e in v.iter_errors(obj):
            failures.append(f"{name}: {'.'.join(str(x) for x in e.path)}: {e.message}")
    assert not failures, "\n".join(failures[:20])


def test_the_pre_fix_schema_would_have_rejected_all_of_them():
    """The landmine was real. Reconstruct it and show the blast radius.

    If this ever stops failing, the enums no longer carry null and the fix has
    been reverted -- which the test above would not necessarily catch, because
    a corpus of only-unscored records would pass both schemas.
    """
    old = copy.deepcopy(_schema())
    for f in ("missingness_reason", "band"):
        old["properties"][f]["enum"] = [e for e in old["properties"][f]["enum"] if e is not None]
    v = jsonschema.Draft7Validator(old)
    verdicts = _verdicts()
    rejected = sum(1 for _, obj in verdicts if list(v.iter_errors(obj)))
    assert rejected == len(verdicts), (
        f"only {rejected} of {len(verdicts)} verdicts trip the pre-fix schema; "
        "the reconstruction no longer reproduces the filed defect"
    )


def test_null_is_in_the_enum_wherever_the_type_allows_it():
    """The general rule, so a NEW nullable field cannot reintroduce the trap."""
    schema = _schema()
    bad = [name for name, spec in schema["properties"].items()
           if isinstance(spec.get("type"), list) and "null" in spec["type"]
           and "enum" in spec and None not in spec["enum"]]
    assert not bad, (
        f"declared nullable but null is absent from the enum: {bad}. "
        "JSON Schema keywords are conjunctive, so these fields can never be null."
    )
