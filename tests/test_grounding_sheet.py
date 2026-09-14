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


# -- the relationship review sheet -------------------------------------------

def _relreview():
    import importlib.util
    import sys as _sys
    spec = importlib.util.spec_from_file_location(
        "relationship_review", REPO / "scripts/relationship_review.py")
    m = importlib.util.module_from_spec(spec)
    _sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


EPISODES = {"episodes": [
    {"episode_id": "e1", "subject_name": "A", "partner_label": "B",
     "stages": ["spouse"], "start": {"value": "2000", "precision": "year"},
     "end": {"value": "2005", "precision": "year"}, "has_reference": True,
     "scorable": True, "defects": [], "ongoing": False, "exclusion_reason": None},
    {"episode_id": "e2", "subject_name": "C", "partner_label": "D",
     "stages": ["unmarried_partner"], "start": None, "end": None,
     "has_reference": False, "scorable": False, "ongoing": False,
     "defects": [{"kind": "no_start_date", "detail": "no candidate carries one"}],
     "exclusion_reason": "defective"},
]}
JOINT = {"jointly_covered": [
    {"domain": "real_life", "a": "A", "b": "B", "period": "2001"}]}


def test_a_load_bearing_episode_sorts_first():
    rows, lb = _relreview().build(EPISODES, JOINT)
    assert rows[0]["subject"] == "A" and rows[0]["load_bearing"] is True
    assert rows[1]["load_bearing"] is False


def test_an_on_screen_pairing_does_not_mark_a_relationship_episode():
    """Only real_life pairings are relationship claims. An on-screen pairing
    sharing the same two names is a different kind of record."""
    onscreen = {"jointly_covered": [
        {"domain": "on_screen", "a": "A", "b": "B", "period": "2001"}]}
    rows, lb = _relreview().build(EPISODES, onscreen)
    assert not any(r["load_bearing"] for r in rows)
    assert lb == set()


def test_an_unreferenced_claim_is_visible():
    rows, _ = _relreview().build(EPISODES, JOINT)
    unref = [r for r in rows if not r["has_reference"]]
    assert len(unref) == 1 and unref[0]["subject"] == "C"


def test_a_dict_shaped_defect_renders_rather_than_raising():
    """Defects are {kind, detail} dicts. Joining them as strings raised, which
    is the right way round -- but the sheet has to render them."""
    mod = _relreview()
    rows, _ = mod.build(EPISODES, JOINT)
    assert isinstance(rows[1]["defects"][0], dict)


def test_no_joint_artifact_means_nothing_is_marked_rather_than_everything():
    rows, lb = _relreview().build(EPISODES, None)
    assert not any(r["load_bearing"] for r in rows)


def test_the_generated_sheet_covers_every_episode():
    import json
    import re
    md = REPO / "docs/RELATIONSHIP-REVIEW.md"
    eps = REPO / "data/pilot/records/episodes.json"
    if not (md.exists() and eps.exists()):
        pytest.skip("needs the generated sheet and the episodes artifact")
    n = len(json.loads(eps.read_text())["episodes"])
    assert len(re.findall(r"^## ", md.read_text(), re.M)) == n, (
        "the sheet must list every episode; review is not sampling"
    )
