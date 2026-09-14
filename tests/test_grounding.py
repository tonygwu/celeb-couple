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


# -- negation awareness: real rationales that the checker used to fail --------

REAL_DENIALS = [
    # Liv Tyler 1997, fable
    "The list is unordered as recorded, so no headline placement or superlative "
    "framing can be inferred; under Rule 3 this is ordinary recognition. obs_1.",
    # Michelle Pfeiffer 2020, fable
    "obs_1 is an all-time selection of 21 names. It is not a single-winner award "
    "or superlative prose, so it does not reach the top band.",
    # Michelle Pfeiffer 2004, fable
    "obs_1 is superlative in scope and could reach the top band. However, the item "
    "is an unordered inclusion on a list whose size is unspecified.",
]


def test_rationales_that_deny_a_top_placement_are_not_failed_for_mentioning_it():
    """Measured 2026-09-14: all three of these real rationales were failed by a
    keyword check, and all three are the judge correctly DECLINING the claim."""
    for rationale in REAL_DENIALS:
        c = _check(rationale, [_obs(etype="unordered_inclusion", length=50)])
        assert c.passed is True, f"false positive on: {rationale[:70]}... -> {c.failures}"


def test_an_actual_top_placement_claim_still_fails():
    c = _check("obs_1 is a headline placement and the top of the list.",
               [_obs(etype="ordered_rank", rank=87, length=100)])
    assert any("top_placement_claim" in f for f in c.failures)


def test_denied_multi_source_language_is_not_failed():
    c = _check("obs_1 is the only judgment; there are not multiple publications here.",
               [_obs()])
    assert c.passed is True


def test_asserted_multi_source_language_still_fails():
    c = _check("obs_1 shows recognition across multiple independent publications.",
               [_obs()])
    assert any("multi_source_claim" in f for f in c.failures)


def test_negation_does_not_reach_across_a_long_distance():
    """A 'not' far earlier must not excuse a later genuine overclaim."""
    filler = "The subject is not a musician. " + ("Context sentence. " * 6)
    c = _check(filler + "obs_1 is a headline placement.",
               [_obs(etype="ordered_rank", rank=87, length=100)])
    assert any("top_placement_claim" in f for f in c.failures)


def test_an_unstated_depth_cannot_support_a_top_placement_claim():
    """Assuming a depth of 100 would let 'ranked 9th' of an unknown list pass."""
    c = _check("obs_1 is a top decile placement.",
               [_obs(etype="ordered_rank", rank=9, length=None)])
    assert any("top_placement_claim" in f for f in c.failures)


# -- the negation window must not cross a sentence boundary ------------------

def test_a_negator_in_the_previous_sentence_does_not_excuse_a_claim():
    """`_asserted` looked back a fixed 60 characters for a negator. That window
    crosses sentence boundaries, so:

        "The list is not ranked in any way. The subject is the winner..."

    had its "winner" claim excused by the "not" belonging to a different
    sentence. The module's own note worries about an unrelated "not" earlier in
    THE SENTENCE; an earlier sentence is worse, and nothing stopped it.

    This is a false NEGATIVE, which is the dangerous direction here: the
    project publishes how many rationales passed these checks, and a check that
    quietly stops firing still reports a pass.
    """
    from modules.consensus.grounding import _asserted, _TOP_CLAIM
    text = "The list is not ranked in any way. The subject is the winner of this award."
    assert _asserted(_TOP_CLAIM, text) is True


def test_a_negator_in_the_same_sentence_still_excuses_the_claim():
    """The behaviour that was wanted, unchanged. Three separate rounds of false
    positives came from careful rationales declining a claim."""
    from modules.consensus.grounding import _asserted, _TOP_CLAIM
    for text in (
        "No headline placement or superlative framing can be inferred here.",
        "It is not a winner of a single-winner award.",
        "The evidence falls short of a top placement.",
    ):
        assert _asserted(_TOP_CLAIM, text) is False, text


def test_boundaries_other_than_a_full_stop_also_separate():
    from modules.consensus.grounding import _asserted, _TOP_CLAIM
    for sep in (". ", "! ", "? ", "\n"):
        text = f"This is not a ranked list{sep}The subject is the winner here."
        assert _asserted(_TOP_CLAIM, text) is True, repr(sep)


def test_an_unnegated_claim_in_a_later_sentence_still_fires():
    from modules.consensus.grounding import _asserted, _TOP_CLAIM
    text = "The subject appeared in the publication. They were the winner."
    assert _asserted(_TOP_CLAIM, text) is True
