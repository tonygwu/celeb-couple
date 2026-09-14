"""Scoring plumbing, with fake judges. No network, no quota."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.llmkit.budget import Budget, BudgetExhausted
from packages.llmkit.contract import load_contract, refuse_mixed_contracts, MixedContractError
from packages.llmkit.judges import FakeJudge, JudgeError, assert_subscription_only
from packages.llmkit.taxonomy import (
    ALL_ERROR_TYPES, E_AUTH_QUOTA, E_CITES_NOTHING, E_SCHEMA, classify_cli_failure,
)
from packages.schema.records import EvidenceType, Lineage, ListEdition, Observation
from packages.temporal.dates import Precision, PreciseDate
from modules.consensus.dossier import build_dossier
from modules.consensus.score import score_dossier

REPO = Path(__file__).resolve().parent.parent
CONTRACT = load_contract(
    REPO / "rubrics/standing/RUBRIC.md",
    REPO / "rubrics/standing/estimate.schema.json",
    "standing-rubric-2.0",
)
RUBRIC = (REPO / "rubrics/standing/RUBRIC.md").read_text()
SCHEMA = (REPO / "rubrics/standing/estimate.schema.json").read_text()


def _pd(v, p=Precision.YEAR):
    return PreciseDate(v, p, "c_1")


EDITION = ListEdition(
    list_edition_id="le_1", publisher="P1", title="The List",
    source_url="https://example.invalid/le_1", published_at=_pd("2010"),
    concerns_period=_pd("2010"), access_route="wikipedia-api",
    retrieved_at_utc="2026-09-14T00:00:00Z", content_sha256="0" * 64,
    candidate_set_described="people in English-language film",
)


def _obs(oid="obs_1"):
    return Observation(
        observation_id=oid, person_id="p_1", list_edition_id="le_1",
        evidence_type=EvidenceType.EDITORIAL_AWARD,
        observed={"award_name": "Example Award", "winner": True},
        concerns_period=_pd("2010"), published_at=_pd("2010-11-18", Precision.DAY),
        lineage=Lineage(original_source="le_1"),
        excerpt="named this year's winner", excerpt_locator="paragraph 1",
    )


def _dossier(obs=None):
    return build_dossier("p_1", "Ada Vance", "2010", obs if obs is not None else [_obs()],
                         {"le_1": EDITION})


def _reply(**over):
    body = {
        "schema_version": "standing-estimate-2.0", "dossier_id": "d",
        "scored": True, "estimate": 91, "band": "90-100",
        "rationale": "obs_1 records a headline award concerning this period.",
        "evidence_ids": ["obs_1"],
        "support": {"reliability": "major_publication",
                    "specificity": "names_appearance_explicitly",
                    "contemporaneity": "contemporaneous",
                    "source_disagreement": "none"},
    }
    body.update(over)
    return json.dumps(body)


def _judge(name, **over):
    return FakeJudge(name, lambda _p: _reply(**over))


def _score(judges, dossier, tmp_path, budget=None):
    return score_dossier(
        dossier, judges, CONTRACT, RUBRIC, SCHEMA,
        budget or Budget(max_calls=50), Path(tmp_path) / "raw",
    )


# -- the happy path ---------------------------------------------------------

def test_two_judges_reduce_to_a_mean_and_keep_both_scores(tmp_path):
    est, verdicts, failures = _score(
        [_judge("fable", estimate=91), _judge("astra", estimate=89)], _dossier(), tmp_path
    )
    assert failures == []
    assert est.estimate == 90.0
    assert est.judges == {"fable": 91.0, "astra": 89.0}
    assert est.reducer == "mean_of_2"
    assert est.support.across_judges_gap == 2.0
    assert est.needs_adjudication is False


def test_a_single_source_award_can_reach_the_top_band(tmp_path):
    """The v2 construct error: publication count must not cap the estimate."""
    est, _, _ = _score([_judge("fable", estimate=92), _judge("astra", estimate=90)],
                       _dossier(), tmp_path)
    assert est.estimate == 91.0
    assert est.support.distinct_original_sources == 1, "one publisher"
    assert est.support.level == "single_source", "thin support, high estimate"


def test_a_wide_judge_gap_escalates_rather_than_averaging_quietly(tmp_path):
    est, _, _ = _score([_judge("fable", estimate=92), _judge("astra", estimate=60)],
                       _dossier(), tmp_path)
    assert est.needs_adjudication is True
    assert est.support.across_judges_gap == 32.0


# -- raw persistence and grounding -----------------------------------------

def test_raw_text_is_written_before_parsing_even_when_parsing_fails(tmp_path):
    bad = FakeJudge("fable", lambda _p: "the model wandered off and wrote prose")
    est, verdicts, failures = _score([bad], _dossier(), tmp_path)
    assert est is None and verdicts == []
    assert failures[0]["error_type"] in ALL_ERROR_TYPES
    raw = Path(tmp_path) / "raw"
    assert list(raw.glob("*fable.txt")), "the raw answer must survive a parse failure"
    assert "wandered off" in list(raw.glob("*fable.txt"))[0].read_text()


def test_a_score_citing_no_observation_is_rejected_as_a_memory_guess(tmp_path):
    j = _judge("fable", evidence_ids=[], rationale="I recall they were striking.")
    _, _, failures = _score([j], _dossier(), tmp_path)
    assert failures[0]["error_type"] == E_CITES_NOTHING


def test_a_score_citing_an_observation_not_in_the_dossier_is_rejected(tmp_path):
    j = _judge("fable", evidence_ids=["obs_from_elsewhere"],
               rationale="obs_from_elsewhere says so")
    _, _, failures = _score([j], _dossier(), tmp_path)
    assert failures[0]["error_type"] == E_SCHEMA


def test_a_rationale_that_names_none_of_its_citations_is_rejected(tmp_path):
    j = _judge("fable", evidence_ids=["obs_1"], rationale="Broadly well regarded.")
    _, _, failures = _score([j], _dossier(), tmp_path)
    assert failures[0]["error_type"] == E_CITES_NOTHING


# -- empty dossiers ---------------------------------------------------------

def test_an_empty_dossier_produces_unscored_not_a_number(tmp_path):
    j = _judge("fable", scored=False, estimate=None, band=None, evidence_ids=[],
               missingness_reason="no_observations",
               rationale="No dated judgment about appearance was supplied.")
    est, _, failures = _score([j], _dossier(obs=[]), tmp_path)
    assert failures == []
    assert est.estimate is None
    assert est.missingness_reason.value == "no_observations"


def test_an_unscored_reply_carrying_an_estimate_is_rejected(tmp_path):
    j = _judge("fable", scored=False, estimate=40)
    _, _, failures = _score([j], _dossier(obs=[]), tmp_path)
    assert failures[0]["error_type"] == E_SCHEMA


def test_an_out_of_range_estimate_is_rejected(tmp_path):
    for bad in (101, -1, "ninety", 90.5):
        _, _, failures = _score([_judge("fable", estimate=bad)], _dossier(), tmp_path)
        assert failures and failures[0]["error_type"] == E_SCHEMA, bad


# -- the budget cap ---------------------------------------------------------

def test_the_cap_halts_before_a_call_and_records_what_was_left(tmp_path):
    budget = Budget(max_calls=1)
    with pytest.raises(BudgetExhausted):
        _score([_judge("fable"), _judge("astra")], _dossier(), tmp_path, budget)
    assert budget.calls_made == 1
    assert budget.halted is True
    assert "budget_cap_reached" in budget.halt_reason
    assert len(budget.remaining_work) == 1, "the halt names the work it did not reach"
    assert budget.remaining_work[0].endswith("/astra")
    assert budget.report()["halted"] is True


def test_the_cap_does_not_degrade_or_retry_past_itself(tmp_path):
    budget = Budget(max_calls=0)
    j = _judge("fable")
    with pytest.raises(BudgetExhausted):
        _score([j], _dossier(), tmp_path, budget)
    assert j.calls == [], "no call may be made once the cap is reached"


# -- billing and contracts --------------------------------------------------

def test_a_visible_api_key_refuses_a_subscription_only_run():
    with pytest.raises(JudgeError) as exc:
        assert_subscription_only({"ANTHROPIC_API_KEY": "sk-ant-whatever"})
    assert exc.value.error_type == E_AUTH_QUOTA
    assert_subscription_only({})  # clean environment is fine


def test_estimates_from_different_rubric_versions_refuse_to_pool():
    with pytest.raises(MixedContractError, match="REFUSING TO POOL"):
        refuse_mixed_contracts([{"contract_id": "aaa"}, {"contract_id": "bbb"}])
    refuse_mixed_contracts([{"contract_id": "aaa"}, {"contract_id": "aaa"}])


def test_quota_exhaustion_is_not_confused_with_a_transient_429():
    assert classify_cli_failure(1, "You've hit your weekly limit", "") == E_AUTH_QUOTA
    assert classify_cli_failure(1, "", "429 rate limit") == "transient_retryable"
    assert classify_cli_failure(1, "", "segfault") == "cli_nonzero_exit"


def test_the_contract_id_covers_the_rubric_and_the_schema(tmp_path):
    r = tmp_path / "r.md"; s = tmp_path / "s.json"
    r.write_text("rubric"); s.write_text("{}")
    a = load_contract(r, s, "v1")
    r.write_text("rubric ")
    b = load_contract(r, s, "v1")
    assert a.contract_id != b.contract_id
