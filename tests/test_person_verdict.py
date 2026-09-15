"""The film-blind person-year judgment, and its cache.

Plan v4 §4a. The per-pairing rubric told the judge which film it was scoring, so
the same person in the same year came back 9.0 for one film and 9.5 for another
— 15 of 57 reused tuples moved more than the 0.28 points by which two judge
families disagree with each other. One judgment per person-year fixes that by
construction.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from modules.pairing.person import (ParseError, cache_key,  # noqa: E402
                                    parse_person_verdict, person_period_id)

_spec = importlib.util.spec_from_file_location("sp", REPO / "scripts/score_person_periods.py")
sp = importlib.util.module_from_spec(_spec)
sys.argv = ["score_person_periods.py", "--backlog-only"]
_spec.loader.exec_module(sp)


def _v(**over) -> str:
    body = {"schema_version": "person-1.0", "person_period_id": "pp_Q1_2000",
            "judged": True, "score": 9.0, "evidence_used": False,
            "evidence_ids": [], "reasoning": "widely covered as striking that year"}
    body.update(over)
    return json.dumps(body)


def test_a_well_formed_verdict_parses():
    v = parse_person_verdict(_v(), "pp_Q1_2000")
    assert (v.judged, v.score, v.evidence_used) == (True, 9.0, False)


def test_json_wrapped_in_a_fence_is_recovered():
    """One family fences every response. A bare json.loads reads 190 of 262
    stored files, raises nothing, and reports a corpus a third short."""
    assert parse_person_verdict("```json\n" + _v() + "\n```", "pp_Q1_2000").score == 9.0


def test_a_verdict_for_a_different_person_year_is_refused():
    with pytest.raises(ParseError, match="not 'pp_Q1_2000'"):
        parse_person_verdict(_v(person_period_id="pp_Q1_2001"), "pp_Q1_2000")


def test_claiming_evidence_without_citing_any_is_refused():
    """`evidence_used: true` with no ids is a claim that cannot be checked, and
    checkability is the entire reason the evidence was attached."""
    with pytest.raises(ParseError, match="no evidence_ids"):
        parse_person_verdict(_v(evidence_used=True, evidence_ids=[]), "pp_Q1_2000")


def test_a_boolean_score_is_not_a_number():
    with pytest.raises(ParseError, match="not a number"):
        parse_person_verdict(_v(score=True), "pp_Q1_2000")


def test_unjudged_requires_a_reason_and_forbids_a_score():
    with pytest.raises(ParseError, match="no cannot_judge_reason"):
        parse_person_verdict(_v(judged=False, score=None), "pp_Q1_2000")
    with pytest.raises(ParseError, match="not judged, but a score"):
        parse_person_verdict(_v(judged=False, cannot_judge_reason="person_unknown"),
                             "pp_Q1_2000")


def test_the_cache_is_keyed_by_family_as_well_as_person_year():
    """Families are separate populations with their own scales — fable's mean
    sits about 0.2 below astra's — so one cached number per person-year would
    average two rulers and report the result as a reading."""
    assert cache_key("Q1", "2000", "fable") != cache_key("Q1", "2000", "astra")
    assert person_period_id("Q1", "2000") in cache_key("Q1", "2000", "fable")


def test_the_prompt_never_names_a_film_or_a_partner():
    """The whole point of §4a. A prompt that mentions either reintroduces the
    context the score is supposed to be free of."""
    p = sp.build_prompt("Someone", "2003", "pp_Q1_2003", [], "<R>", "<S>")
    low = p.lower()
    for banned in ("film:", "co-star", "partner", "relationship with", "pairing"):
        assert banned not in low, f"the prompt mentions {banned!r}"
    assert "perceived to be in 2003" in p


def test_absence_of_evidence_is_stated_not_left_silent():
    """Silence would read as a signal. Most person-years have no observation."""
    p = sp.build_prompt("Someone", "2003", "pp_Q1_2003", [], "<R>", "<S>")
    assert "None supplied" in p
    assert "not evidence of a low score" in p


def test_supplied_evidence_is_rendered_with_its_id_and_quote():
    obs = [{"observation_id": "obs_1", "concerns_period": "2003",
            "evidence_type": "editorial_award", "observed": {"award_name": "Sexiest Man Alive"},
            "excerpt": "Someone — Sexiest Man Alive 2003"}]
    p = sp.build_prompt("Someone", "2003", "pp_Q1_2003", obs, "<R>", "<S>")
    assert "obs_1" in p and "Sexiest Man Alive" in p


def test_evidence_is_bounded_to_nearby_years():
    obs = [{"person_id": "Q1", "concerns_period": "2003", "observation_id": "near"},
           {"person_id": "Q1", "concerns_period": "2009", "observation_id": "far"},
           {"person_id": "Q2", "concerns_period": "2003", "observation_id": "other"}]
    got = {o["observation_id"] for o in sp.evidence_for(obs, "Q1", "2003")}
    assert got == {"near"}


def test_needed_tuples_deduplicates_the_person_years():
    """The whole reason the cache exists: 119 pairings need 215 person-years,
    not 238 person-slots."""
    pairings = {"pairings": [
        {"male_qid": "M", "female_qid": "W", "period": "2000", "male": "m", "female": "w"},
        {"male_qid": "M", "female_qid": "W2", "period": "2000", "male": "m", "female": "w2"},
    ]}
    got = sp.needed_tuples(pairings)
    assert len(got) == 3, got          # M/2000 once, not twice
