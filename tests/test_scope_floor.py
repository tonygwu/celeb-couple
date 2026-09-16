"""Two rules decide who appears, and nobody is removed by hand.

An earlier version removed four performers BY NAME because their careers are
mostly pre-1980. That is roster selection for presentation, which
docs/SOURCE-HUNT.md warns against: the roster was chosen on prominence BEFORE
anything was scored, on purpose. It was replaced by two uniform rules -- a 1980
floor and a 3-romance bar -- which nobody has to be chosen for. These guards
keep the rules stated on the page and stop a hand-picked list returning.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROSTER = json.loads((REPO / "docs/seed-roster.json").read_text())


def test_nobody_is_removed_from_the_roster_by_name():
    """The four are back. If a hand-picked exclusion list reappears, the rules
    have stopped being the thing that decides."""
    everyone = set(ROSTER["men"]) | set(ROSTER["women"])
    for who in ("Audrey Hepburn", "Sophia Loren", "Paul Newman", "Robert Redford"):
        assert who in everyone, f"{who} was removed by hand; use the rules instead"
    assert "removed_2026_09_16" not in ROSTER


def test_the_roster_records_the_rules_and_why_hand_removal_was_dropped():
    r = ROSTER["rules"]
    assert r["min_year"] == 1980 and r["min_pairings"] == 3
    assert r["statement"] and r["why_no_hand_removals"]


def test_the_roster_stays_balanced_by_sex():
    assert len(ROSTER["men"]) == len(ROSTER["women"]), (
        f"{len(ROSTER['men'])} men against {len(ROSTER['women'])} women")


def test_both_stages_default_to_the_same_floor():
    a = (REPO / "scripts/build_imdb_pairings.py").read_text()
    b = (REPO / "scripts/rebuild_boards.py").read_text()
    for src in (a, b):
        assert '"--min-year", type=int, default=1980' in src


def test_the_bar_is_three_romances():
    src = (REPO / "scripts/rebuild_boards.py").read_text()
    assert '"--min-pairings", type=int, default=3' in src


def test_the_bar_is_display_only_and_says_so():
    """A person below the bar keeps their pairings and still appears as someone
    else's partner. Hiding them from the data would be a different thing."""
    src = (REPO / "scripts/rebuild_boards.py").read_text()
    assert "DISPLAY ONLY" in src
    html = (REPO / "web/board.html").read_text()
    assert "still appears as a partner" in html or "still appear as partners" in html


def test_the_trajectory_obeys_the_floor_too():
    src = (REPO / "scripts/rebuild_boards.py").read_text()
    assert 'if int(per) < args.min_year:' in src


def test_the_floor_is_reported_not_silent():
    src = (REPO / "scripts/rebuild_boards.py").read_text()
    assert "scope floor {args.min_year}: dropped" in src
    pair = (REPO / "scripts/build_imdb_pairings.py").read_text()
    assert 'dropped[f"film before the {args.min_year} scope floor"]' in pair


def test_the_page_states_both_rules():
    html = (REPO / "web/board.html").read_text()
    assert 'id="scope"' in html
    assert "min_pairings" in html and "min_year" in html


def test_each_board_reports_how_many_the_bar_hides():
    """A threshold nobody can see is the same problem as a silent exclusion."""
    assert '"below_bar"' in (REPO / "scripts/rebuild_boards.py").read_text()
    assert "below_bar" in (REPO / "web/board.html").read_text()


def test_the_stage_that_spends_applies_the_floor_first():
    src = (REPO / "scripts/build_imdb_pairings.py").read_text()
    assert src.index("--min-year") < src.index("person_years_needed")
