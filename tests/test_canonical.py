"""One canonical score per person-year, averaged over every grading of it."""
from __future__ import annotations

import pytest

from modules.pairing.canonical import (
    GradingError, MODEL_FOR_FAMILY, canonical_scores, coverage,
    normalise_grading, refuse_pooled_contracts,
)


def entry(qid="Q1", period="2006", family="fable", score=9.0, judged=True, **kw):
    e = {"person_id": qid, "person": "A Person", "period": period, "family": family,
         "judged": judged, "score": score, "evidence_used": False,
         "contract": {"contract_id": "c993828d0a86"}}
    e.update(kw)
    return e


def grad(**kw):
    return normalise_grading(entry(**kw), source="test")


def test_the_canonical_score_is_the_mean_of_every_grading():
    """The operator's five measured tuples: 2 fable, 1 opus, 1 sonnet."""
    gs = [grad(family="fable", score=9.9), grad(family="fable", score=10.0),
          grad(family="opus", score=9.8), grad(family="sonnet", score=9.5)]
    c = canonical_scores(gs)[("Q1", "2006")]
    assert c["score"] == pytest.approx((9.9 + 10.0 + 9.8 + 9.5) / 4)
    assert c["n"] == 4
    assert c["models"] == ["claude-fable-5-1", "claude-opus-5", "claude-sonnet-5"]


def test_an_unjudged_grading_is_a_refusal_and_never_averages_as_zero():
    """astra refused 23 of 215 person-years. Averaging those in as 0.0 would
    drag every one of them to the bottom of the board."""
    gs = [grad(score=9.0), grad(family="astra", judged=False, score=None)]
    c = canonical_scores(gs)[("Q1", "2006")]
    assert c["score"] == 9.0 and c["n"] == 1


def test_a_person_year_with_no_judged_grading_is_absent_not_zero():
    assert canonical_scores([grad(judged=False, score=None)]) == {}


def test_the_spread_reports_the_disagreement_the_average_hides():
    gs = [grad(score=8.5), grad(family="opus", score=9.0)]
    assert canonical_scores(gs)[("Q1", "2006")]["spread"] == pytest.approx(0.5)


def test_a_single_grading_has_zero_spread_and_n_one():
    c = canonical_scores([grad(score=8.5)])[("Q1", "2006")]
    assert c["n"] == 1 and c["spread"] == 0.0


def test_averaging_is_exact_and_not_binary_float_drift():
    """Fraction(str(x)), never Fraction(float). The mirroring guarantee the
    boards rest on depends on this."""
    gs = [grad(score=0.1), grad(family="opus", score=0.2)]
    assert canonical_scores(gs)[("Q1", "2006")]["score"] == pytest.approx(0.15)


def test_the_noisy_model_is_tagged_so_the_decision_stays_reversible():
    gs = [grad(score=9.0), grad(family="sonnet", score=9.5)]
    c = canonical_scores(gs)[("Q1", "2006")]
    assert c["noisy_included"] == ["claude-sonnet-5"]


def test_a_model_can_be_excluded_without_regrading_anything():
    gs = [grad(score=9.0), grad(family="sonnet", score=9.5)]
    c = canonical_scores(gs, exclude_models=("claude-sonnet-5",))[("Q1", "2006")]
    assert c["n"] == 1 and c["score"] == 9.0


def test_the_model_is_recovered_from_the_family_for_older_entries():
    """Entries written before 2026-09-16 carry no `model` field."""
    assert grad(family="astra")["model"] == MODEL_FOR_FAMILY["astra"]


def test_an_explicit_model_field_wins_over_the_family_default():
    assert grad(family="fable", model="claude-fable-5-2")["model"] == "claude-fable-5-2"


def test_an_unknown_family_raises_rather_than_defaulting():
    with pytest.raises(GradingError, match="MODEL_FOR_FAMILY"):
        grad(family="mystery")


def test_a_missing_timestamp_is_recorded_as_unknown_not_invented():
    """mtime says when a file was touched, not when the judgment was made."""
    g = grad()
    assert g["graded_at_utc"] is None and g["graded_at_known"] is False


def test_a_supplied_timestamp_is_kept_and_marked_known():
    g = grad(graded_at_utc="2026-09-16T03:52:00Z")
    assert g["graded_at_known"] is True


def test_pooling_two_contracts_for_one_person_year_is_refused():
    """Two contract ids are two different questions; their mean means nothing."""
    gs = [grad(score=9.0),
          grad(family="opus", score=9.0, contract={"contract_id": "OTHER"})]
    with pytest.raises(GradingError, match="different questions"):
        refuse_pooled_contracts(canonical_scores(gs))


def test_one_contract_across_many_gradings_passes():
    refuse_pooled_contracts(canonical_scores([grad(score=9.0), grad(family="opus", score=9.1)]))


def test_coverage_reports_a_taxonomy_not_a_bare_count():
    gs = [grad(qid="Q1", score=9.0), grad(qid="Q1", family="opus", score=9.4),
          grad(qid="Q2", score=7.0)]
    cov = coverage(canonical_scores(gs))
    assert cov["person_years"] == 2
    assert cov["by_grading_count"] == {1: 1, 2: 1}
    assert cov["multiply_graded"] == 1
    assert cov["mean_spread_where_multiple"] == pytest.approx(0.4)
