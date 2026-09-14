from __future__ import annotations

from modules.consensus.grounding import check_rationale


def _obs(oid="obs_1", etype="editorial_award", pub="PEOPLE", period="2002",
         rank=None, length=None, src=None):
    return {"observation_id": oid, "evidence_type": etype, "publisher": pub,
            "concerns_period": period, "rank": rank, "list_length": length,
            "original_source": src or f"le_{period}", "excerpt": "named winner"}


def _check(rationale, observations, cited=("obs_1",), estimate=92.0):
    return check_rationale(
        estimate_id="se_1", person="Ada", period="2002", estimate=estimate,
        rationale=rationale, cited_ids=list(cited),
        dossier_ids=[o["observation_id"] for o in observations],
        observations=observations)


def test_a_clean_rationale_passes():
    c = _check("obs_1 records a dated award naming the subject.", [_obs()])
    assert c.passed is True
    assert "cites_at_least_one_observation" not in c.failures


def test_claiming_several_publications_on_one_source_fails():
    c = _check("obs_1 shows recognition across multiple independent publications.",
               [_obs()])
    assert not c.passed
    assert any("multi_source_claim" in f for f in c.failures)


def test_claiming_repeated_recognition_from_one_period_fails():
    c = _check("obs_1 shows the subject was consistently recognised year after year.",
               [_obs()])
    assert any("repetition_claim" in f for f in c.failures)


def test_claiming_a_top_placement_with_no_supporting_observation_fails():
    low = _obs(etype="ordered_rank", rank=87, length=100)
    c = _check("obs_1 is a top-of-the-list placement.", [low])
    assert any("top_placement_claim" in f for f in c.failures)


def test_a_genuine_top_ten_placement_supports_a_top_claim():
    top = _obs(etype="ordered_rank", rank=5, length=100)
    c = _check("obs_1 is a top decile placement.", [top])
    assert c.passed is True


def test_an_award_supports_a_headline_claim():
    c = _check("obs_1 is the headline award for the year.", [_obs()])
    assert c.passed is True


def test_citing_nothing_fails():
    c = _check("The subject was widely admired.", [_obs()], cited=())
    assert "cites_at_least_one_observation" in c.failures


def test_citing_an_observation_not_in_the_dossier_fails():
    c = _check("obs_elsewhere supports this.", [_obs()], cited=("obs_elsewhere",))
    assert any("every_cited_id_exists" in f for f in c.failures)


def test_a_rationale_that_never_names_its_citations_fails():
    c = _check("The evidence is strong.", [_obs()])
    assert "rationale_names_the_ids_it_cites" in c.failures


def test_a_top_band_estimate_from_one_source_warns_rather_than_fails():
    """Legitimate under the rubric, so it is flagged for a human, not rejected."""
    c = _check("obs_1 is the headline award.", [_obs()], estimate=92.0)
    assert c.passed is True
    assert c.needs_human_read is True
    assert any("worth a human read" in w for w in c.warnings)


def test_two_publishers_across_two_periods_support_the_stronger_claims():
    obs = [_obs("obs_1", period="2002", src="le_a"),
           _obs("obs_2", pub="Esquire", period="2004", src="le_b")]
    c = check_rationale(
        estimate_id="se", person="Ada", period="2002", estimate=88.0,
        rationale="obs_1 and obs_2 show repeated recognition across multiple publications.",
        cited_ids=["obs_1", "obs_2"], dossier_ids=["obs_1", "obs_2"], observations=obs)
    assert c.passed is True


def test_the_evidence_summary_is_built_for_a_human_to_read_beside_the_claim():
    c = _check("obs_1 records a dated award.", [_obs(etype="ordered_rank", rank=5,
                                                     length=100)])
    assert c.evidence_summary
    assert "rank 5 of 100" in c.evidence_summary[0]


def test_the_rubrics_own_band_language_does_not_count_as_a_repetition_claim():
    """Measured 2026-09-14: a correct single-period rationale failed because it
    quoted the rubric band 'the judgments consistently present the person as
    notably attractive'. A judge naming the band it chose is not claiming
    multi-year recognition, and a check that fires on correct work is ignored."""
    c = _check(
        "obs_1 is a top-five finish among 100, which the rubric treats as "
        "consistent presentation of the person as notably attractive (band 75-89).",
        [_obs(etype="ordered_rank", rank=5, length=100)], estimate=86.0)
    assert c.passed is True, c.failures
    assert any("band language" in w for w in c.warnings), (
        "it should still be flagged for a human, just not failed"
    )


def test_an_unambiguous_multi_year_claim_still_fails_on_one_period():
    for phrasing in ("recognised year after year",
                     "named across several years",
                     "repeatedly named by the magazine",
                     "on multiple occasions"):
        c = _check(f"obs_1 shows the subject was {phrasing}.", [_obs()])
        assert any("repetition_claim" in f for f in c.failures), phrasing
