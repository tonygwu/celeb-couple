"""Invariants the four boards must satisfy, whatever the judgments are.

Boards 3 and 4 are mirrors of 1 and 2, so the mirroring must be EXACT rather
than approximate. It is the same Fraction with its sign flipped, which is why
the module converts decimals with `Fraction(str(x))` and never `Fraction(0.4)`.
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from modules.pairing.boards import (contributions_for, exact,  # noqa: E402
                                    paw_rate, paw_total)

_gaps = st.decimals(min_value=-3, max_value=3, places=1).map(str)
_cents = st.sampled_from(["0.0", "0.4", "0.7", "1.0"])


@st.composite
def _records(draw, n=st.integers(min_value=1, max_value=8)):
    out = []
    for i in range(draw(n)):
        out.append({
            "pairing_id": f"p{i}", "domain": draw(st.sampled_from(["on_screen", "real_life"])),
            "period": "2000", "work": None,
            "gap": draw(_gaps), "centrality": draw(_cents),
            "male_qid": "M", "female_qid": "W", "male": "Man", "female": "Woman",
        })
    return out


@given(_records())
@settings(max_examples=150, deadline=None)
def test_the_two_sides_of_every_pairing_mirror_exactly(recs):
    m = paw_total(contributions_for(recs, "M"))
    w = paw_total(contributions_for(recs, "W"))
    assert m == -w, (m, w)


@given(_records())
@settings(max_examples=150, deadline=None)
def test_the_arithmetic_is_exact_not_floating_point(recs):
    # The whole board is Fractions. A float creeping in would make the mirror
    # test above pass by luck at small n and fail at large n.
    for c in contributions_for(recs, "M"):
        assert isinstance(c.paw, Fraction)
        assert isinstance(c.weight, Fraction) and isinstance(c.signed_gap, Fraction)


@given(_records())
@settings(max_examples=150, deadline=None)
def test_a_zero_centrality_pairing_contributes_nothing(recs):
    kept = [r for r in recs if exact(r["centrality"]) != 0]
    assert (paw_total(contributions_for(recs, "M"))
            == paw_total(contributions_for(kept, "M")))


@given(_records())
@settings(max_examples=100, deadline=None)
def test_order_does_not_change_a_total(recs):
    a = paw_total(contributions_for(recs, "M"))
    b = paw_total(contributions_for(list(reversed(recs)), "M"))
    assert a == b


@given(_records())
@settings(max_examples=100, deadline=None)
def test_someone_elses_pairings_never_change_a_total(recs):
    mine = paw_total(contributions_for(recs, "M"))
    others = [{**r, "male_qid": "OTHER", "female_qid": "OTHER2",
               "pairing_id": r["pairing_id"] + "x"} for r in recs]
    assert paw_total(contributions_for(recs + others, "M")) == mine


def test_rate_is_none_rather_than_zero_when_nothing_qualifies():
    """No qualifying pairing is a different statement from an average of zero,
    and a board that renders them alike invites the wrong reading."""
    recs = [{"pairing_id": "p", "domain": "on_screen", "period": "2000",
             "work": None, "gap": "1.0", "centrality": "0.0",
             "male_qid": "M", "female_qid": "W", "male": "m", "female": "w"}]
    assert paw_rate(contributions_for(recs, "M")) is None


def test_an_unjudged_pairing_is_skipped_not_counted_as_zero():
    recs = [{"pairing_id": "p", "domain": "on_screen", "period": "2000",
             "work": None, "gap": None, "centrality": "1.0",
             "male_qid": "M", "female_qid": "W", "male": "m", "female": "w"}]
    assert contributions_for(recs, "M") == []


def test_a_missing_centrality_is_skipped_not_defaulted_to_one():
    """Defaulting would silently promote an unclassified co-appearance to a
    full romance, putting a couple on the board who were never a couple."""
    recs = [{"pairing_id": "p", "domain": "on_screen", "period": "2000",
             "work": None, "gap": "1.0", "centrality": None,
             "male_qid": "M", "female_qid": "W", "male": "m", "female": "w"}]
    assert contributions_for(recs, "M") == []


def test_negative_paw_is_representable_and_is_the_point():
    # Someone paired consistently below their own level. Brad Pitt scoring
    # negative is the statistic working, not failing.
    recs = [{"pairing_id": "p", "domain": "on_screen", "period": "2000",
             "work": None, "gap": "-0.6", "centrality": "1.0",
             "male_qid": "M", "female_qid": "W", "male": "m", "female": "w"}]
    assert paw_total(contributions_for(recs, "M")) == Fraction(-3, 5)


def test_someone_with_only_zero_centrality_pairings_is_not_on_the_board():
    """They have no romance to score. Listing them at +0.00 reads as
    "measured, and came out even", which is the confusion paw_rate returns None
    to avoid. Caught on a dry run: 8 of 20 rows on the partial board were
    people whose only pairings were cast-list co-appearances."""
    from modules.pairing.boards import build_board
    recs = [{"pairing_id": "p", "domain": "on_screen", "period": "2000",
             "work": "Ensemble", "gap": "1.0", "centrality": "0.0",
             "male_qid": "M", "female_qid": "W", "male": "Man", "female": "Woman"}]
    assert build_board(recs, gender="male", domain="on_screen",
                       names={"M": "Man"}, min_pairings=1) == []


def test_a_person_with_one_real_romance_among_co_appearances_still_qualifies():
    from modules.pairing.boards import build_board
    recs = [
        {"pairing_id": "p1", "domain": "on_screen", "period": "2000", "work": "A",
         "gap": "1.0", "centrality": "0.0", "male_qid": "M", "female_qid": "W",
         "male": "Man", "female": "Woman"},
        {"pairing_id": "p2", "domain": "on_screen", "period": "2001", "work": "B",
         "gap": "0.4", "centrality": "1.0", "male_qid": "M", "female_qid": "W2",
         "male": "Man", "female": "Woman2"},
    ]
    rows = build_board(recs, gender="male", domain="on_screen",
                       names={"M": "Man"}, min_pairings=1)
    assert len(rows) == 1
    # The zero-weight pairing must not inflate the pairing count either.
    assert rows[0]["pairings"] == 1
    assert abs(rows[0]["paw_total"] - 0.4) < 1e-9
