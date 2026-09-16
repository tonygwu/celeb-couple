"""The board covers 1980 onward, and SAYS SO.

Four performers were removed because their careers are mostly earlier. That is
a roster change made partly for presentation, which docs/SOURCE-HUNT.md warns
against: the roster was chosen on prominence BEFORE anything was scored, on
purpose. It is acceptable only as a STATED SCOPE, never a silent exclusion, and
these guards are what keep it stated.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROSTER = json.loads((REPO / "docs/seed-roster.json").read_text())
REMOVED = {"Audrey Hepburn", "Sophia Loren", "Paul Newman", "Robert Redford"}


def test_the_removed_four_are_not_on_the_roster():
    assert not (REMOVED & (set(ROSTER["men"]) | set(ROSTER["women"])))


def test_the_roster_records_who_was_removed_and_why():
    r = ROSTER["removed_2026_09_16"]
    assert set(r["who"]) == REMOVED
    assert r["why"] and r["cost"], "a removal with no recorded reason is a silent one"


def test_the_roster_stays_balanced_by_sex():
    """Dropping four people must not quietly tilt the cohort."""
    assert len(ROSTER["men"]) == len(ROSTER["women"]), (
        f"{len(ROSTER['men'])} men against {len(ROSTER['women'])} women")


def test_the_roster_file_name_matches_its_contents():
    """It used to be seed-30.json and now holds 26. A name that states a count
    becomes a lie the first time the count changes."""
    n = len(ROSTER["men"]) + len(ROSTER["women"])
    assert not (REPO / f"docs/seed-{n}.json").exists() or n == 30
    assert (REPO / "docs/seed-roster.json").exists()


def test_both_stages_default_to_the_same_floor():
    """Two floors that disagree would let a pairing through one and not the
    other, and the page would report a scope it does not keep."""
    a = (REPO / "scripts/build_imdb_pairings.py").read_text()
    b = (REPO / "scripts/rebuild_boards.py").read_text()
    for src in (a, b):
        assert '"--min-year", type=int, default=1980' in src


def test_the_trajectory_obeys_the_floor_too():
    """A person scored in 1978 for a pairing the floor removed still stretched
    the shared x-axis to 1978, which is what made this visible."""
    src = (REPO / "scripts/rebuild_boards.py").read_text()
    assert 'if int(per) < args.min_year:' in src


def test_the_floor_is_reported_not_silent():
    src = (REPO / "scripts/rebuild_boards.py").read_text()
    assert "scope floor {args.min_year}: dropped" in src
    pair = (REPO / "scripts/build_imdb_pairings.py").read_text()
    assert 'dropped[f"film before the {args.min_year} scope floor"]' in pair


def test_the_page_states_the_scope():
    html = (REPO / "web/board.html").read_text()
    assert 'id="scope"' in html
    for who in REMOVED:
        assert who.split()[-1] in html, f"{who} is excluded but not named on the page"


def test_the_stage_that_spends_applies_the_floor_first():
    """The floor lives in build_imdb_pairings so score_person_periods never
    pays for a person-year the board cannot show."""
    src = (REPO / "scripts/build_imdb_pairings.py").read_text()
    assert src.index("--min-year") < src.index("person_years_needed")


def test_the_floor_does_not_gut_one_persons_prime():
    """The floor was first set to 1990. It cut 101 pairings and the loss landed
    on three people: Pfeiffer -33%, Gere -27%, Cruise -25%, while 17 of 26
    seeds lost nothing. A floor whose cost is that concentrated is a bias."""
    note = ROSTER["removed_2026_09_16"].get("floor_note", "")
    assert "1990" in note and "Pfeiffer" in note, (
        "the reason 1990 was rejected must stay recorded, or someone will "
        "raise the floor again for the same wrong reason")


def test_removal_from_the_roster_is_not_a_ban():
    """They are off the SEED list, so their filmographies are not pulled. They
    are not excluded from the data: Robert Redford still appears opposite
    Michelle Pfeiffer in Up Close & Personal, and counts like any other
    non-seed partner. The page must not claim otherwise."""
    assert "what_removal_means" in ROSTER["removed_2026_09_16"]
    html = (REPO / "web/board.html").read_text()
    assert "not excluded" in html, (
        "the page says four people are outside the scope; it must also say they "
        "still count where they appear opposite someone we follow")
