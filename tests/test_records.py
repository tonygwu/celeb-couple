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


def test_a_rank_without_a_stated_depth_keeps_the_depth_unknown():
    """Found by audit: a prose mention saying only "topping the ranking" was
    being merged as "1 of 100". Rank 1 of 100 reads far more selective than
    "first, of an unstated list", and the depth is the fact that decides it."""
    ok = _obs(EvidenceType.ORDERED_RANK, {
        "rank": 1, "list_length": None, "order_is_ranking": True,
        "order_basis": "the article says she topped the ranking"})
    assert ok.observed["list_length"] is None
    with pytest.raises(SchemaError, match="list_length is required"):
        _obs(EvidenceType.ORDERED_RANK, {
            "rank": 1, "order_is_ranking": True, "order_basis": "x"})
    with pytest.raises(SchemaError, match=">= rank"):
        _obs(EvidenceType.ORDERED_RANK, {
            "rank": 50, "list_length": 10, "order_is_ranking": True,
            "order_basis": "x"})


# -- booleans are not integers, whatever isinstance says ---------------------

def _ranked(rank, length):
    return _obs(EvidenceType.ORDERED_RANK,
                {"rank": rank, "list_length": length, "order_is_ranking": True,
                 "order_basis": "the page reads 'The Results, counting down'"})


def test_a_boolean_rank_is_refused():
    """`isinstance(True, int)` is True and `True >= 1` is True, so a bare
    `"rank": true` validated and became rank 1 -- the TOP of the list, and the
    most consequential value it could have taken."""
    with pytest.raises(SchemaError, match="positive integer"):
        _ranked(True, 50)


def test_a_boolean_list_length_is_refused_for_a_ranked_observation():
    """`True < rank` is False when rank is 1, so "ranked 1 of true" validated
    and would render as "Ranked 1 of 1"."""
    with pytest.raises(SchemaError, match="integer"):
        _ranked(1, True)


def test_a_boolean_list_length_is_refused_for_an_unordered_inclusion():
    with pytest.raises(SchemaError, match="real size"):
        _obs(EvidenceType.UNORDERED_INCLUSION, {"list_length": True})


def test_ordinary_integers_still_validate():
    _ranked(12, 50)
    _obs(EvidenceType.UNORDERED_INCLUSION, {"list_length": 15})


def test_a_boolean_vote_share_is_refused():
    """`0 <= True <= 1` is True, so `"vote_share": true` validated as a share
    of 1.0 -- a claim that the subject took 100% of the ballot."""
    with pytest.raises(SchemaError, match=r"\[0, 1\]"):
        _obs(EvidenceType.BALLOT_PREFERENCE,
             {"vote_share": True, "ballot_description": "reader vote among 20"})


def test_an_ordinary_vote_share_still_validates():
    _obs(EvidenceType.BALLOT_PREFERENCE,
         {"vote_share": 0.3, "ballot_description": "reader vote among 20"})


def test_a_publication_rating_must_be_a_number():
    """The field is documented as "the PUBLICATION's number on the
    PUBLICATION's scale" and only its presence was checked. A string rendered
    into the dossier as 'gave its own rating of very high on its own 10 scale'
    and went to a judge looking like a measurement."""
    with pytest.raises(SchemaError, match="number"):
        _obs(EvidenceType.PUBLICATION_RATING,
             {"rating_value": "very high", "rating_scale": "0-10"})


def test_a_boolean_publication_rating_is_refused():
    with pytest.raises(SchemaError, match="number"):
        _obs(EvidenceType.PUBLICATION_RATING,
             {"rating_value": True, "rating_scale": "0-10"})


def test_an_ordinary_publication_rating_still_validates():
    _obs(EvidenceType.PUBLICATION_RATING,
         {"rating_value": 7.5, "rating_scale": "0-10"})


# -- label provenance and lookup failures ------------------------------------

def test_a_failed_label_lookup_is_distinguishable_from_a_missing_label():
    """Both end as "still a bare Q-id" and the caller could not tell them
    apart. That ambiguity already cost an investigation: Q13909 was first
    diagnosed as a label-SERVICE failure and turned out to have no English
    label at all, in any batch, ever."""
    from modules.records import wikidata
    assert hasattr(wikidata, "LOOKUP_FAILURES")
    assert isinstance(wikidata.LOOKUP_FAILURES, list)


def test_label_provenance_is_recorded_per_person():
    """A name taken from an English Wikipedia article title is different
    provenance from a name taken from a Wikidata label. Both are sourced; they
    are not the same source."""
    from modules.records import wikidata
    assert hasattr(wikidata, "LABEL_SOURCES")
    assert isinstance(wikidata.LABEL_SOURCES, dict)


# -- coverage must not count partners in a cohort numerator ------------------

def _coverage(observed_qids, cohort_qids):
    """The corrected computation, as both producers now implement it."""
    from collections import Counter
    per_person = Counter(observed_qids)
    cohort = set(cohort_qids)
    with_any = sorted(q for q in cohort if per_person.get(q))
    return {
        "cohort_people_with_any_observation": len(with_any),
        "cohort_people_total": len(cohort),
        "people_with_observations_including_partners": len(per_person),
    }


def test_a_partners_observation_does_not_cover_a_cohort_member():
    """The artifact said "covering 14 of 14 people" and listed 5 cohort members
    with none, in the same block. The numerator counted every person with an
    observation -- partners included -- against a cohort-only denominator, and
    the two happened to reach the same number.

    The honest figure is 9 of 14. The report's headline overstated coverage by
    five people, in the flattering direction.
    """
    cohort = ["c1", "c2", "c3"]
    observed = ["c1", "c1", "partner_a", "partner_b"]   # only c1 is in cohort
    cov = _coverage(observed, cohort)
    assert cov["cohort_people_with_any_observation"] == 1
    assert cov["cohort_people_total"] == 3
    assert cov["people_with_observations_including_partners"] == 3


def test_the_two_counts_are_reported_separately():
    """Partner observations are valuable -- they are what makes a pairing
    jointly covered -- so the number is worth keeping. It just is not cohort
    coverage."""
    cov = _coverage(["c1", "p1"], ["c1", "c2"])
    assert cov["cohort_people_with_any_observation"] == 1
    assert cov["people_with_observations_including_partners"] == 2
    assert cov["cohort_people_with_any_observation"] <= cov["cohort_people_total"]


def test_coverage_and_people_with_none_must_reconcile():
    """`people_with_none` was written by fetch_observations and never
    recomputed by the merge, so a prose mention that gave Liv Tyler her first
    observation left her on the list. Deriving the coverage count as
    `total - len(people_with_none)` then inherited the staleness and reported 9
    where ten cohort members had evidence.

    Two derived numbers over the same corpus must add up. This checks the live
    artifact where it exists, which is the only place the bug could appear.
    """
    import json
    from pathlib import Path
    f = Path(__file__).resolve().parent.parent / "data/pilot/observations/observations.json"
    if not f.exists():
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")

    blob = json.loads(f.read_text())
    cov = blob["coverage"]
    assert (cov["cohort_people_with_any_observation"] + len(cov["people_with_none"])
            == cov["cohort_people_total"]), cov

    # And nobody on the "none" list may actually carry an observation.
    observed = {o["person_id"] for o in blob["observations"]}
    cohort = json.loads(
        (Path(__file__).resolve().parent.parent / "docs/pilot-cohort.json").read_text())
    by_name = {p["display_name"]: p["wikidata_qid"] for p in cohort["people"]}
    wrongly_listed = [n for n in cov["people_with_none"]
                      if by_name.get(n) in observed]
    assert not wrongly_listed, (
        f"listed as having no observations but they do: {wrongly_listed}")
