"""A constant sex offset cannot reorder the RATE board. It can reorder cumulative.

Plan v3 §2 stated the identity and v4 inherits it unchanged:

    ΔPAW_total(p) = δ · scored_exposure(p)   — differs per person, so it reorders
    ΔPAW_rate(p)  = δ                        — identical for everyone, so it cannot

Measured 2026-09-15 on the M1 corpus: the judges score women about 0.44 higher
than men on the shared scale (astra +0.36, fable +0.56), and both families agree
on the direction. Whether that is Hollywood casting or the model calibrating one
scale differently by sex is NOT decidable from these data.

It does not have to be. The rate board is invariant to it either way, which is
why the rate board is the one to read when the question is "who punched above
their weight" rather than "who had the most romances".
"""

from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from modules.pairing.boards import build_board  # noqa: E402

_NAMES = {"M1": "A", "M2": "B", "M3": "C", "W1": "X", "W2": "Y", "W3": "Z"}


@st.composite
def _corpus(draw):
    recs = []
    # Deliberately UNEQUAL exposure per man: that is what makes the cumulative
    # board sensitive to an offset while the rate board is not.
    for i, man in enumerate(("M1", "M2", "M3"), start=1):
        for j in range(draw(st.integers(min_value=1, max_value=4))):
            recs.append({
                "pairing_id": f"p{man}{j}", "domain": "on_screen",
                "period": "2000", "work": f"F{j}",
                "gap": float(draw(st.decimals(min_value=-2, max_value=2, places=1))),
                "centrality": float(draw(st.sampled_from([0.4, 0.7, 1.0]))),
                "male_qid": man, "female_qid": f"W{(j % 3) + 1}",
                "male": _NAMES[man], "female": _NAMES[f"W{(j % 3) + 1}"],
            })
    return recs


def _order(rows, key):
    return [r["name"] for r in sorted(rows, key=lambda r: (-(r[key] or 0), r["name"]))]


def _shift(recs, delta):
    """Shift every gap by delta, EXACTLY.

    `r["gap"] - delta` in float is not exact, and the difference is not
    cosmetic here. Hypothesis found a draw where two men tie at a rate of
    exactly -1.0: shifting by -0.32 in float gives one of them
    -0.6799999999999999 and the other -0.6799999999999998, one ULP apart, so
    the tie breaks and the name tie-break reverses them. The board module
    itself is exact -- `Fraction(str(x))`, never `Fraction(0.4)` -- so a float
    shift here tests the helper's arithmetic rather than the module's, and
    fails about one run in ten.
    """
    d = Fraction(str(delta))
    return [{**r, "gap": str(Fraction(str(r["gap"])) - d)} for r in recs]


@given(_corpus(), st.decimals(min_value=-1, max_value=1, places=2))
@settings(max_examples=200, deadline=None)
def test_a_constant_offset_never_reorders_the_rate_board(recs, delta):
    d = float(delta)
    a = build_board(recs, gender="male", domain="on_screen", names=_NAMES, min_pairings=1)
    b = build_board(_shift(recs, d), gender="male", domain="on_screen",
                    names=_NAMES, min_pairings=1)
    assert _order(a, "paw_rate") == _order(b, "paw_rate")


@given(_corpus(), st.decimals(min_value=-1, max_value=1, places=2))
@settings(max_examples=200, deadline=None)
def test_every_rate_moves_by_exactly_the_offset(recs, delta):
    """The identity itself, not just its consequence. If this fails the
    implementation is wrong even when the ordering happens to survive."""
    d = float(delta)
    a = {r["name"]: r["paw_rate"] for r in
         build_board(recs, gender="male", domain="on_screen", names=_NAMES, min_pairings=1)}
    b = {r["name"]: r["paw_rate"] for r in
         build_board(_shift(recs, d), gender="male", domain="on_screen",
                     names=_NAMES, min_pairings=1)}
    for name, before in a.items():
        assert abs((b[name] - before) - -d) < 1e-9, (name, before, b[name], d)


def test_a_constant_offset_CAN_reorder_the_cumulative_board():
    """Not a defect — a property, and the reason the rate column exists.

    Because Δtotal = δ·exposure, a person with more romances moves further. On
    the real M1 board, removing the measured +0.44 offset took Ben Affleck from
    #1 to #2 on men's real-life, behind Colin Jost.
    """
    recs = [
        # One man, many thin romances; another, few strong ones.
        *({"pairing_id": f"pA{i}", "domain": "on_screen", "period": "2000",
           "work": f"F{i}", "gap": 0.5, "centrality": 1.0,
           "male_qid": "M1", "female_qid": "W1", "male": "A", "female": "X"}
          for i in range(6)),
        {"pairing_id": "pB0", "domain": "on_screen", "period": "2000", "work": "G",
         "gap": 1.6, "centrality": 1.0,
         "male_qid": "M2", "female_qid": "W2", "male": "B", "female": "Y"},
    ]
    before = _order(build_board(recs, gender="male", domain="on_screen",
                                names=_NAMES, min_pairings=1), "paw_total")
    after = _order(build_board(_shift(recs, 0.44), gender="male", domain="on_screen",
                               names=_NAMES, min_pairings=1), "paw_total")
    assert before == ["A", "B"], before
    assert after == ["B", "A"], after


def test_a_tie_between_two_men_survives_the_shift():
    """The exact draw hypothesis failed on, pinned so it cannot come back.

    B and C both rate exactly -1.0 before the shift, so the name tie-break puts
    B first. A shift is a constant, so they must still tie afterwards and B must
    still be first. With a float shift they land one ULP apart and swap.
    """
    recs = [
        {"pairing_id": "pM10", "domain": "on_screen", "period": "2000",
         "work": "F0", "gap": 0.0, "centrality": 0.4, "male_qid": "M1",
         "female_qid": "W1", "male": "A", "female": "X"},
        {"pairing_id": "pM20", "domain": "on_screen", "period": "2000",
         "work": "F0", "gap": -1.0, "centrality": 0.4, "male_qid": "M2",
         "female_qid": "W1", "male": "B", "female": "X"},
        {"pairing_id": "pM30", "domain": "on_screen", "period": "2000",
         "work": "F0", "gap": -1.4, "centrality": 1.0, "male_qid": "M3",
         "female_qid": "W1", "male": "C", "female": "X"},
        {"pairing_id": "pM31", "domain": "on_screen", "period": "2000",
         "work": "F1", "gap": 0.0, "centrality": 0.4, "male_qid": "M3",
         "female_qid": "W2", "male": "C", "female": "Y"},
    ]
    before = build_board(recs, gender="male", domain="on_screen",
                         names=_NAMES, min_pairings=1)
    after = build_board(_shift(recs, -0.32), gender="male", domain="on_screen",
                        names=_NAMES, min_pairings=1)
    rates = {r["name"]: r["paw_rate"] for r in before}
    assert rates["B"] == rates["C"] == -1.0
    assert _order(before, "paw_rate") == _order(after, "paw_rate") == ["A", "B", "C"]
