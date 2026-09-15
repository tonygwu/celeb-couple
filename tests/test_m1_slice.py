"""The M1 slice is chosen by a fixed rule, before anything is judged.

Plan v3's cohort was selected on stated criteria before any check of how easy
each person was to score, and v4 keeps that discipline: a slice picked after
seeing results is a slice picked to flatter them.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SLICE = REPO / "data/roster100/run/m1_slice.json"


def _slice() -> dict:
    if not SLICE.exists():
        pytest.skip("data/ is gitignored; run scripts/select_m1_slice.py")
    return json.loads(SLICE.read_text())


def test_the_rule_is_recorded_with_the_slice():
    # A selection rule that lives only in a commit message cannot be checked
    # against the thing it produced.
    s = _slice()
    assert "BOTH domains" in s["selection_rule"]
    assert "before any judging" in s["selection_rule"]


def test_the_slice_is_gender_balanced():
    """Boards 3 and 4 are mirrors of 1 and 2. A slice of only men would leave
    the women's boards with one pairing each and validate nothing."""
    s = _slice()
    genders = [f["gender"] for f in s["focal"]]
    assert genders.count("male") == genders.count("female"), genders


def test_every_focal_actor_appears_in_both_domains():
    s = _slice()
    for f in s["focal"]:
        assert f["real_life_pairings"] > 0, f
        assert f["on_screen_pairings"] > 0, f


def test_both_domains_are_represented_in_the_pairings():
    s = _slice()
    assert s["counts"]["on_screen"] > 0 and s["counts"]["real_life"] > 0


def test_every_pairing_touches_a_focal_actor():
    s = _slice()
    focal = {f["qid"] for f in s["focal"]}
    orphans = [p["pairing_id"] for p in s["pairings"]
               if not (focal & {p["male_qid"], p["female_qid"]})]
    assert not orphans, orphans[:5]


def test_pairing_ids_are_unique():
    """A film with two focal actors is emitted twice by the scan. A duplicate
    would be judged twice and counted twice on the board."""
    s = _slice()
    ids = [p["pairing_id"] for p in s["pairings"]]
    assert len(ids) == len(set(ids)), "duplicate pairing ids"


def test_every_pairing_carries_a_four_digit_year():
    # A year-precision date must never become January 1, and a pairing with no
    # date cannot be judged "at the time of this pairing" at all.
    s = _slice()
    bad = [p["pairing_id"] for p in s["pairings"]
           if not (isinstance(p["period"], str) and p["period"].isdigit()
                   and len(p["period"]) == 4)]
    assert not bad, bad[:5]


def test_selection_is_deterministic():
    """Same inputs, same slice. The tie-break is the Wikidata id, which is
    arbitrary and STABLE rather than arbitrary and not."""
    if not SLICE.exists():
        pytest.skip("data/ is gitignored")
    before = SLICE.read_text()
    out = subprocess.run(
        [sys.executable, str(REPO / "scripts/select_m1_slice.py")],
        cwd=REPO, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    after = json.loads(SLICE.read_text())
    first = json.loads(before)
    assert [f["qid"] for f in first["focal"]] == [f["qid"] for f in after["focal"]]
    assert ([p["pairing_id"] for p in first["pairings"]]
            == [p["pairing_id"] for p in after["pairings"]])


def test_every_pairing_names_both_people():
    """A prompt that names nobody wastes a call.

    Real-life partners are usually NOT on the roster -- that is what makes them
    partners -- so looking their names up there returned None and the prompt
    read `Man: **None**`. The judge refused 49 of those rather than guessing,
    which is rubric rule 4 working correctly and 49 calls spent for nothing.
    Names come from the episode's own `subject_name` / `partner_label` now.
    """
    s = _slice()
    nameless = [p["pairing_id"] for p in s["pairings"]
                if not (p.get("male") and p.get("female"))]
    assert not nameless, nameless[:5]


def test_a_pairing_dropped_for_a_missing_name_is_counted():
    # Silently dropping one is a pairing the board will not have, with nothing
    # to say so. A count of zero is the only evidence nothing was lost.
    assert "skipped_for_missing_name" in _slice()


def test_every_on_screen_pairing_names_its_film():
    s = _slice()
    untitled = [p["pairing_id"] for p in s["pairings"]
                if p["domain"] == "on_screen" and not p.get("work")]
    assert not untitled, untitled[:5]
