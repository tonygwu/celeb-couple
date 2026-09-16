"""Weight and confidence are different axes, and the filter must use weight.

Filtering on confidence let Alec Baldwin's one-scene cameo in Notting Hill onto
the board as a Julia Roberts pairing, because the judge was correctly CERTAIN
the relationship existed. Certainty is not screen time.
"""
from __future__ import annotations

import json

import pytest

from modules.pairing.couples import (
    BOARD_WEIGHTS, CoupleVerdictError, board_pairs, build_prompt, cache_key,
    excluded_pairs, parse_couples_verdict,
)


def pair(a, b, weight, conf="high", billed=True):
    return {"a": a, "b": b, "characters": f"{a} and {b}", "weight": weight,
            "in_billed_list": billed, "confidence": conf}


NOTTING_HILL = {"pairs": [
    pair("Hugh Grant", "Julia Roberts", "central"),
    pair("Tim McInnerny", "Gina McKee", "substantial", billed=False),
    pair("Rhys Ifans", "Emma Chambers", "incidental", billed=False),
    # the real case: certain it exists, one scene, must NOT reach the board
    pair("Julia Roberts", "Alec Baldwin", "incidental", conf="high", billed=False),
]}


def test_a_high_confidence_incidental_pair_is_not_a_board_row():
    got = {(p["a"], p["b"]) for p in board_pairs(NOTTING_HILL)}
    assert ("Julia Roberts", "Alec Baldwin") not in got, (
        "Jeff King has one scene; a filter on confidence alone put him on the "
        "board as a Julia Roberts pairing"
    )
    assert ("Hugh Grant", "Julia Roberts") in got


def test_the_second_couple_of_a_love_triangle_survives():
    """The operator's rule: a love triangle is two separate pairings."""
    jgwi = {"pairs": [pair("Adam Sandler", "Jennifer Aniston", "central"),
                      pair("Adam Sandler", "Brooklyn Decker", "substantial"),
                      pair("Nicole Kidman", "Dave Matthews", "incidental")]}
    got = {(p["a"], p["b"]) for p in board_pairs(jgwi)}
    assert ("Adam Sandler", "Brooklyn Decker") in got
    assert len(got) == 2


def test_excluded_pairs_is_the_exact_complement():
    """Exclusions stay countable. A pair may never vanish from both lists."""
    keep, drop = board_pairs(NOTTING_HILL), excluded_pairs(NOTTING_HILL)
    assert len(keep) + len(drop) == len(NOTTING_HILL["pairs"])
    assert not {id(p) for p in keep} & {id(p) for p in drop}


def test_a_low_confidence_central_pair_still_reaches_the_board():
    """Weight decides board membership. Confidence is reported, not applied."""
    v = {"pairs": [pair("A Actor", "B Actor", "central", conf="low")]}
    assert len(board_pairs(v)) == 1


@pytest.mark.parametrize("weight", BOARD_WEIGHTS)
def test_every_board_weight_is_actually_kept(weight):
    assert board_pairs({"pairs": [pair("A", "B", weight)]})


def test_markdown_fenced_json_is_recovered():
    """One judge family fences its JSON and the other does not."""
    body = json.dumps(NOTTING_HILL)
    assert parse_couples_verdict(f"Here you go:\n```json\n{body}\n```\n")["pairs"]


def test_an_unreadable_weight_raises_rather_than_defaulting():
    """Defaulting to incidental deletes board rows; defaulting to central
    invents them. Both are worse than failing on one film."""
    bad = json.dumps({"pairs": [dict(pair("A", "B", "central"), weight="major")]})
    with pytest.raises(CoupleVerdictError, match="weight"):
        parse_couples_verdict(bad)


def test_a_missing_field_raises():
    p = pair("A", "B", "central"); del p["confidence"]
    with pytest.raises(CoupleVerdictError, match="confidence"):
        parse_couples_verdict(json.dumps({"pairs": [p]}))


def test_a_person_paired_with_themselves_raises():
    with pytest.raises(CoupleVerdictError, match="themselves"):
        parse_couples_verdict(json.dumps({"pairs": [pair("Ann Lee", "ann lee", "central")]}))


def test_an_empty_pair_list_is_a_valid_answer():
    """A film with no romance must be representable, or the judge will invent one."""
    assert parse_couples_verdict('{"pairs": []}')["pairs"] == []


def test_non_json_raises():
    with pytest.raises(CoupleVerdictError):
        parse_couples_verdict("I could not determine the couples in this film.")


def test_cache_key_separates_judge_families():
    assert cache_key("tt0125439", "fable") != cache_key("tt0125439", "opus")


def test_the_prompt_names_an_unbilled_lead_as_expected():
    """Good Will Hunting: IMDb's ten rows contain no Minnie Driver. The prompt
    has to tell the judge that absence is normal, or it will not name her."""
    cast = [(1, "nm0000245", "actor", '["Sean"]'), (2, "nm0000354", "actor", '["Will"]')]
    text = build_prompt("Good Will Hunting", 1997, cast,
                        "RUBRIC BODY", {"nm0000245": "Robin Williams",
                                        "nm0000354": "Matt Damon"})
    assert "RUBRIC BODY" in text
    assert "Good Will Hunting (1997)" in text
    assert "Robin Williams as [\"Sean\"]" in text
    assert "in_billed_list" in text


def test_the_prompt_refuses_an_empty_title():
    with pytest.raises(ValueError):
        build_prompt("", 1997, [], "R", {})
