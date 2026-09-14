"""Adversarial cases against the measurement assumptions.

Each test names the unjustified inference it exists to prevent.
"""

from __future__ import annotations

import dataclasses

import pytest

from packages.schema.records import (
    ADJUDICATION_GAP,
    EvidenceType,
    Lineage,
    ListEdition,
    MissingnessReason,
    Observation,
    SchemaError,
    StandingEstimate,
    Support,
    reduce_judges,
)
from packages.temporal.dates import Precision, PreciseDate


def _pd(v: str, p: Precision = Precision.YEAR) -> PreciseDate:
    return PreciseDate(v, p, "c_1")


def _obs(etype: EvidenceType, observed: dict, **kw) -> Observation:
    base = dict(
        observation_id="obs_1",
        person_id="p_1",
        list_edition_id="le_1",
        evidence_type=etype,
        observed=observed,
        concerns_period=_pd("2010"),
        published_at=_pd("2010-08-17", Precision.DAY),
        lineage=Lineage(original_source="le_1"),
        excerpt="12. Ada Vance",
        excerpt_locator="gallery slide 39 of 50",
    )
    base.update(kw)
    return Observation(**base)


# -- the inferred/observed boundary ---------------------------------------

def test_standing_estimate_has_no_status_field_at_all():
    """Every project estimate is inferred. A status field could leak 'observed'."""
    names = {f.name for f in dataclasses.fields(StandingEstimate)}
    assert "status" not in names
    assert "observed" not in names


def test_a_publication_rating_lives_only_on_the_observation():
    o = _obs(EvidenceType.PUBLICATION_RATING, {"rating_value": 8, "rating_scale": "1-10"})
    assert o.observed["rating_value"] == 8
    assert not hasattr(o, "estimate")


def test_matching_numbers_are_allowed_provenance_is_what_is_tested():
    """A publication's 74 and our 74 may coincide. Test the transformation, not equality."""
    pub = _obs(EvidenceType.PUBLICATION_RATING, {"rating_value": 74, "rating_scale": "0-100"})
    est = StandingEstimate(
        estimate_id="se_1", person_id="p_1", periods=("2010",),
        estimate=74.0, rubric_version="standing-rubric-2.0", contract_id="abc123",
        judges={"fable": 75.0, "astra": 73.0}, reducer="mean_of_2",
        evidence_ids=("obs_1",), support=None,
        rationale="cites obs_1; the publication's own 74 is one judgment among others",
    )
    assert est.estimate == pub.observed["rating_value"]        # coincidence is fine
    assert est.method == "RES"                                  # produced by RES
    assert est.rubric_version == "standing-rubric-2.0"
    assert "obs_1" in est.evidence_ids                          # and it cites its evidence


# -- omission and gallery order -------------------------------------------

def test_there_is_no_evidence_type_for_non_appearance():
    """Omission cannot be written down, so it cannot move a score."""
    values = {e.value for e in EvidenceType}
    for forbidden in ("non_appearance", "omission", "absent", "not_listed"):
        assert forbidden not in values


def test_gallery_order_is_not_ranking_order():
    with pytest.raises(SchemaError, match="order_is_ranking"):
        _obs(EvidenceType.ORDERED_RANK, {"rank": 3, "list_length": 15})


def test_a_rank_needs_the_page_text_that_establishes_it():
    with pytest.raises(SchemaError, match="order_basis"):
        _obs(
            EvidenceType.ORDERED_RANK,
            {"rank": 3, "list_length": 15, "order_is_ranking": True},
        )


def test_an_unordered_inclusion_may_not_carry_a_rank():
    with pytest.raises(SchemaError, match="may not"):
        _obs(EvidenceType.UNORDERED_INCLUSION, {"rank": 3, "list_length": 15})


def test_an_award_is_not_a_rank():
    with pytest.raises(SchemaError, match="not a rank"):
        _obs(
            EvidenceType.EDITORIAL_AWARD,
            {"award_name": "Example Award", "rank": 1},
        )


# -- ballots ---------------------------------------------------------------

def test_a_thirty_percent_share_of_a_twenty_way_ballot_is_not_a_plurality():
    """30% can still place second behind 35%. v2 called this a plurality."""
    with pytest.raises(SchemaError, match="place second"):
        _obs(
            EvidenceType.BALLOT_PREFERENCE,
            {
                "vote_share": 0.30,
                "ballot_description": "reader vote among 20 editor-shortlisted men",
                "is_plurality": True,
            },
        )


def test_a_share_is_kept_without_a_placement_when_the_outcome_is_unpublished():
    o = _obs(
        EvidenceType.BALLOT_PREFERENCE,
        {
            "vote_share": 0.30,
            "ballot_description": "reader vote among 20 editor-shortlisted men",
        },
    )
    assert o.observed["vote_share"] == 0.30
    assert "placement" not in o.observed
    assert "is_plurality" not in o.observed


def test_a_ballot_share_needs_the_ballot_described():
    with pytest.raises(SchemaError, match="ballot_description"):
        _obs(EvidenceType.BALLOT_PREFERENCE, {"vote_share": 0.30})


# -- syndication ------------------------------------------------------------

def test_syndicated_copies_name_one_original_source():
    copies = [
        _obs(
            EvidenceType.UNORDERED_INCLUSION,
            {"list_length": 15},
            observation_id=f"obs_{i}",
            lineage=Lineage(original_source="le_canonical", is_syndicated_copy=i > 0),
        )
        for i in range(5)
    ]
    assert len({c.lineage.original_source for c in copies}) == 1
    support = Support(
        distinct_original_sources=1, distinct_publishers=1,
        reliability="major_publication", specificity="names appearance",
        contemporaneity="contemporaneous",
    )
    assert support.level == "single_source"


# -- scoring and missingness -----------------------------------------------

def test_an_empty_dossier_yields_unscored_with_a_reason_not_a_number():
    est = StandingEstimate(
        estimate_id="se_2", person_id="p_1", periods=("2016",),
        estimate=None, rubric_version="standing-rubric-2.0", contract_id="abc123",
        judges={}, reducer="mean_of_2", evidence_ids=(), support=None, rationale="",
        missingness_reason=MissingnessReason.NO_OBSERVATIONS,
    )
    assert est.estimate is None
    assert est.missingness_reason is MissingnessReason.NO_OBSERVATIONS


def test_an_unscored_estimate_must_say_why():
    with pytest.raises(SchemaError, match="must say why"):
        StandingEstimate(
            estimate_id="se_3", person_id="p_1", periods=("2016",), estimate=None,
            rubric_version="r", contract_id="c", judges={}, reducer="mean_of_2",
            evidence_ids=(), support=None, rationale="",
        )


def test_a_score_that_cites_no_observation_is_refused_as_a_memory_guess():
    with pytest.raises(SchemaError, match="model-memory guess"):
        StandingEstimate(
            estimate_id="se_4", person_id="p_1", periods=("2016",), estimate=88.0,
            rubric_version="r", contract_id="c", judges={"fable": 88.0},
            reducer="mean_of_2", evidence_ids=(), support=None, rationale="looks right",
        )


def test_nearby_period_reuse_keeps_one_estimate_identity_for_several_periods():
    est = StandingEstimate(
        estimate_id="se_5", person_id="p_1", periods=("2015", "2016", "2017"),
        estimate=78.0, rubric_version="r", contract_id="c",
        judges={"fable": 79.0, "astra": 77.0}, reducer="mean_of_2",
        evidence_ids=("obs_1",), support=None,
        rationale="2016 evidence, reused for the adjacent years within the bound",
        period_support="nearby_period",
    )
    assert len(est.periods) == 3
    assert est.estimate_id == "se_5", "one identity, so the simulation draws it once"


def test_duplicate_period_keys_are_refused():
    with pytest.raises(SchemaError, match="duplicate period"):
        StandingEstimate(
            estimate_id="se_6", person_id="p_1", periods=("2016", "2016"),
            estimate=70.0, rubric_version="r", contract_id="c", judges={},
            reducer="mean_of_2", evidence_ids=("obs_1",), support=None, rationale="x",
        )


# -- the two-judge reducer ---------------------------------------------------

def test_the_two_judge_reducer_is_a_mean_and_is_named_one():
    value, escalate = reduce_judges({"fable": 79.0, "astra": 77.0})
    assert value == 78.0
    assert escalate is False


def test_a_wide_judge_gap_escalates_instead_of_being_silently_averaged():
    value, escalate = reduce_judges({"fable": 90.0, "astra": 60.0})
    assert value == 75.0
    assert escalate is True, f"a gap of 30 exceeds ADJUDICATION_GAP={ADJUDICATION_GAP}"


def test_list_edition_requires_its_candidate_pool_described():
    kw = dict(
        list_edition_id="le_1", publisher="P", title="T",
        source_url="https://example.invalid/x", published_at=_pd("2010"),
        concerns_period=_pd("2010"), access_route="wikipedia-api",
        retrieved_at_utc="2026-09-14T00:00:00Z", content_sha256="0" * 64,
    )
    with pytest.raises(SchemaError, match="candidate_set_described"):
        ListEdition(candidate_set_described="", **kw)
    assert ListEdition(candidate_set_described="women in English-language film", **kw)


def test_an_unstated_list_size_is_none_and_never_zero():
    """A prose mention rarely states a size. Recording that as 0 rendered to the
    judge as 'a set of 0 names', which is not merely odd but misleading about how
    selective the list was. One real scored observation carried it."""
    ok = _obs(EvidenceType.UNORDERED_INCLUSION, {"list_length": None})
    assert ok.observed["list_length"] is None
    with pytest.raises(SchemaError, match="not a real size"):
        _obs(EvidenceType.UNORDERED_INCLUSION, {"list_length": 0})
    with pytest.raises(SchemaError, match="not a real size"):
        _obs(EvidenceType.UNORDERED_INCLUSION, {"list_length": -3})
    with pytest.raises(SchemaError, match="list_length is required"):
        _obs(EvidenceType.UNORDERED_INCLUSION, {})
