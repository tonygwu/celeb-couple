"""Merging judge families keeps the disagreement visible instead of averaging it away.

Plan v4 §5. Two families judging the same pairing give a CROSS-FAMILY spread,
which is a better quantity than repeat noise within one family: it measures
whether a judgment is a property of the rubric or of the model that made it.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location("build_boards", REPO / "scripts/build_boards.py")
bb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bb)


def _fam(judge: str, gap, centrality, pid="p1"):
    return {"pairings": [{
        "pairing_id": pid, "domain": "on_screen", "period": "2003", "work": "F",
        "male": "Man", "female": "Woman", "male_qid": "M", "female_qid": "W",
        "gap": gap, "judges": {judge: gap} if gap is not None else {},
        "centrality": centrality}]}


def test_two_families_reduce_to_their_mean_and_keep_both_values():
    recs, _ = bb.merge_families([_fam("fable", 0.6, 1.0), _fam("astra", 0.2, 1.0)])
    assert len(recs) == 1
    assert abs(recs[0]["gap"] - 0.4) < 1e-9
    assert recs[0]["family_gaps"] == {"fable": 0.6, "astra": 0.2}


def test_the_spread_is_reported_not_averaged_away():
    recs, _ = bb.merge_families([_fam("fable", 0.6, 1.0), _fam("astra", 0.2, 1.0)])
    xf = bb.cross_family_spread(recs)
    assert xf["pairings_both_judged"] == 1
    assert abs(xf["gap_spreads"][0] - 0.4) < 1e-9


def test_a_pairing_only_one_family_judged_reports_no_spread():
    """One judgment has no measurable disagreement. It does not have zero
    disagreement, and rendering them alike would claim a precision that was
    never measured."""
    recs, _ = bb.merge_families([_fam("fable", 0.6, 1.0), _fam("astra", None, None)])
    assert recs[0]["gap"] == 0.6
    assert bb.cross_family_spread(recs)["pairings_both_judged"] == 0


def test_a_centrality_flip_to_zero_is_visible_in_the_merge():
    """The case that matters most: one family says there is a romance and the
    other says there is none. The pairing leaves the board entirely, which moves
    a total further than any disagreement about the gap."""
    recs, _ = bb.merge_families([_fam("fable", 0.6, 1.0), _fam("astra", 0.6, 0.0)])
    fc = recs[0]["family_centralities"]
    assert min(fc.values()) == 0.0 and max(fc.values()) > 0
    assert bb.cross_family_spread(recs)["centrality_spreads"] == [1.0]


def test_merging_one_family_is_a_no_op_on_the_values():
    recs, _ = bb.merge_families([_fam("fable", 0.6, 0.7)])
    assert recs[0]["gap"] == 0.6 and recs[0]["centrality"] == 0.7


def test_distinct_pairings_do_not_merge_into_each_other():
    a = _fam("fable", 0.6, 1.0, pid="p1")
    b = _fam("astra", -0.4, 1.0, pid="p2")
    recs, _ = bb.merge_families([a, b])
    assert {r["pairing_id"] for r in recs} == {"p1", "p2"}
    assert bb.cross_family_spread(recs)["pairings_both_judged"] == 0
