"""The pairing verdict parser: the gap is primary, and the absolutes must agree.

Plan v4 §4. v3 scored two people in separate calls and subtracted, and labelling
the drift between those two absolute judgments is the entire reason
`modules/analytics/comparability.py` exists. A relative judgment has no drift to
label, so the gap is asked for directly and the absolutes are demoted to a
consistency check.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from modules.pairing.judge import (ABSOLUTE_TOLERANCE, ParseError,  # noqa: E402
                                   parse_pairing_verdict)


def _v(**over) -> str:
    body = {"schema_version": "pairing-1.0", "pairing_id": "p1", "judged": True,
            "gap": 0.4, "f_absolute": 9.8, "m_absolute": 9.4, "centrality": 1.0,
            "reasoning": "she was styled as the film's romantic focus"}
    body.update(over)
    return json.dumps(body)


def test_a_well_formed_verdict_parses():
    v = parse_pairing_verdict(_v(), "p1")
    assert (v.judged, v.gap, v.f_absolute, v.centrality) == (True, 0.4, 9.8, 1.0)


def test_json_wrapped_in_prose_is_recovered():
    text = "Here is my judgment:\n```json\n" + _v() + "\n```\nHope that helps."
    assert parse_pairing_verdict(text, "p1").gap == 0.4


def test_a_negative_gap_is_a_normal_answer():
    # The statistic exists to produce these. Brad Pitt scoring negative is the
    # measure working, not failing.
    assert parse_pairing_verdict(_v(gap=-0.6, f_absolute=9.2, m_absolute=9.8), "p1").gap == -0.6


def test_absolutes_that_contradict_the_gap_are_refused():
    with pytest.raises(ParseError, match="self-contradictory"):
        parse_pairing_verdict(_v(gap=0.4, f_absolute=9.0, m_absolute=9.4), "p1")


def test_rounding_drift_within_tolerance_is_allowed():
    # 9.8 - 9.4 = 0.4000000000000004 in binary floating point, and a judge may
    # round either number by a step. Neither is a contradiction.
    parse_pairing_verdict(_v(gap=0.5, f_absolute=9.8, m_absolute=9.4), "p1")
    with pytest.raises(ParseError):
        parse_pairing_verdict(_v(gap=0.4 + ABSOLUTE_TOLERANCE * 2,
                                 f_absolute=9.8, m_absolute=9.4), "p1")


def test_absolutes_are_optional_because_they_are_secondary():
    v = parse_pairing_verdict(_v(f_absolute=None, m_absolute=None), "p1")
    assert v.gap == 0.4 and v.f_absolute is None


def test_a_boolean_gap_is_not_a_number():
    """`isinstance(True, int)` is True in Python, so `"gap": true` would become
    1.0 -- a real gap, indistinguishable in the artifact from one the judge
    meant. The sibling parser was bitten by exactly this on `estimate`."""
    with pytest.raises(ParseError, match="not a number"):
        parse_pairing_verdict(_v(gap=True), "p1")


def test_a_verdict_for_a_different_pairing_is_refused():
    # The judge answering about the wrong pairing must never be filed under this
    # one; the whole artifact would be quietly mislabelled.
    with pytest.raises(ParseError, match="not 'p1'"):
        parse_pairing_verdict(_v(pairing_id="p2"), "p1")


def test_unjudged_requires_a_reason_and_forbids_a_gap():
    with pytest.raises(ParseError, match="no cannot_judge_reason"):
        parse_pairing_verdict(_v(judged=False, gap=None), "p1")
    with pytest.raises(ParseError, match="not judged, but a gap"):
        parse_pairing_verdict(_v(judged=False, cannot_judge_reason="person_unknown"), "p1")
    v = parse_pairing_verdict(
        _v(judged=False, gap=None, f_absolute=None, m_absolute=None,
           centrality=None, cannot_judge_reason="not_a_romance"), "p1")
    assert v.judged is False and v.cannot_judge_reason == "not_a_romance"


def test_out_of_range_values_are_refused():
    for over, msg in ((dict(gap=12), "outside -10..10"),
                      (dict(f_absolute=11), "outside 0..10"),
                      (dict(centrality=1.5), "outside 0..1")):
        with pytest.raises(ParseError, match=msg):
            parse_pairing_verdict(_v(**over), "p1")


def test_an_empty_reasoning_is_refused():
    with pytest.raises(ParseError, match="reasoning is empty"):
        parse_pairing_verdict(_v(reasoning="   "), "p1")


def test_the_wrong_schema_version_is_refused():
    with pytest.raises(ParseError, match="schema_version"):
        parse_pairing_verdict(_v(schema_version="pairing-0.9"), "p1")
