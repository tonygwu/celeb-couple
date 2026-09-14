"""The human review sheet must lead with the rationales that carry a claim.

34 of 39 rationales are flagged for a human read, and the plan budgets 60-90
minutes for that plus the relationship checks. Only the estimates feeding a
jointly covered pairing produce the signed gaps the report publishes; the rest
are worth reading and change no published number if they wait.

Ordering by that is a workflow improvement and not a relaxed standard: every
rationale is still on the sheet, and none is dropped or summarised.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def test_the_load_bearing_rationales_come_first():
    md = REPO / "docs/GROUNDING-AUDIT.md"
    joint = REPO / "data/pilot/run/joint_with_nearby.json"
    if not (md.exists() and joint.exists()):
        pytest.skip("needs the generated sheet and the joint artifact")

    headings = re.findall(r"^## (.+)$", md.read_text(), re.M)
    flags = [("LOAD-BEARING" in h) for h in headings]
    assert any(flags), (
        "no rationale is marked load-bearing. `person` carries the judge in "
        "brackets and the joint artifact names people plainly, so matching the "
        "raw strings silently matches nothing and looks like a real result."
    )
    first_unflagged = flags.index(False)
    assert all(flags[:first_unflagged]), "flagged entries must be contiguous"
    assert not any(flags[first_unflagged:]), (
        "a load-bearing entry appears after an ordinary one; the operator "
        "reading top-down would miss it"
    )


def test_every_side_of_every_covered_pairing_is_marked():
    """If a pairing's estimate is not on the sheet, the gap it produces has no
    reviewable rationale at all."""
    md = REPO / "docs/GROUNDING-AUDIT.md"
    joint = REPO / "data/pilot/run/joint_with_nearby.json"
    if not (md.exists() and joint.exists()):
        pytest.skip("needs the generated sheet and the joint artifact")

    blob = json.loads(joint.read_text())
    need = set()
    for j in blob.get("jointly_covered", []):
        need.add((j["a"], j.get("a_src") or j["period"]))
        need.add((j["b"], j.get("b_src") or j["period"]))

    text = md.read_text()
    missing = [f"{p} {per}" for p, per in sorted(need)
               if not re.search(rf"^## {re.escape(p)}.*— {per} —.*LOAD-BEARING",
                                text, re.M)]
    assert not missing, f"covered-pairing estimates not marked on the sheet: {missing}"


def test_nothing_was_dropped_from_the_sheet():
    """Ordering must not become filtering."""
    md = REPO / "docs/GROUNDING-AUDIT.md"
    js = REPO / "data/pilot/run/grounding_audit.json"
    if not (md.exists() and js.exists()):
        pytest.skip("needs the generated sheet and its artifact")
    n_headings = len(re.findall(r"^## ", md.read_text(), re.M))
    assert n_headings == len(json.loads(js.read_text())["checks"])
