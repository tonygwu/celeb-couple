"""What reaches a judge, and what must never reach one."""

from __future__ import annotations

from packages.schema.records import EvidenceType, Lineage, ListEdition, Observation
from packages.temporal.dates import Precision, PreciseDate
from modules.consensus.dossier import build_dossier, collapse_syndication


def _pd(v, p=Precision.YEAR):
    return PreciseDate(v, p, "c_1")


def _edition(eid, publisher, title="The List"):
    return ListEdition(
        list_edition_id=eid, publisher=publisher, title=title,
        source_url=f"https://example.invalid/{eid}",
        published_at=_pd("2010"), concerns_period=_pd("2010"),
        access_route="wikipedia-api", retrieved_at_utc="2026-09-14T00:00:00Z",
        content_sha256="0" * 64,
        candidate_set_described="people in English-language film",
    )


def _rank_obs(oid, eid, rank, original=None, syndicated=False):
    return Observation(
        observation_id=oid, person_id="p_1", list_edition_id=eid,
        evidence_type=EvidenceType.ORDERED_RANK,
        observed={
            "rank": rank, "list_length": 50, "order_is_ranking": True,
            "order_basis": "page reads 'The Results, counting down from 50'",
        },
        concerns_period=_pd("2010"), published_at=_pd("2010-08-17", Precision.DAY),
        lineage=Lineage(original_source=original or eid, is_syndicated_copy=syndicated),
        excerpt="12. Ada Vance", excerpt_locator="slide 39 of 50",
    )


EDITIONS = {"le_1": _edition("le_1", "P1"), "le_2": _edition("le_2", "P2")}


# -- isolation --------------------------------------------------------------

def test_a_dossier_never_mentions_a_partner_a_roster_or_another_person():
    d = build_dossier("p_1", "Ada Vance", "2010", [_rank_obs("obs_1", "le_1", 12)], EDITIONS)
    lowered = d.text.lower()
    for leak in ("partner", "roster", "rank 1 overall", "compared with", "couple",
                 "paired", "relationship", "married", "dating"):
        assert leak not in lowered, f"dossier leaked {leak!r}"


def test_anonymised_dossier_hides_the_name_for_the_identity_leakage_check():
    named = build_dossier("p_1", "Ada Vance", "2010", [_rank_obs("o", "le_1", 12)], EDITIONS)
    anon = build_dossier(
        "p_1", "Ada Vance", "2010", [_rank_obs("o", "le_1", 12)], EDITIONS, anonymise=True
    )
    assert "Ada Vance" in named.text
    assert "[SUBJECT]" in anon.text
    # the name must be gone from EXCERPTS too, not only the Subject line --
    # a ranked-list excerpt reads "12. Ada Vance" and hands over the identity
    assert "Ada Vance" not in anon.text
    assert "Vance" not in anon.text
    assert "quoted: '12. [SUBJECT]'" in anon.text
    # the evidence itself is unchanged, so any score difference is leakage
    assert named.observation_ids == anon.observation_ids


def test_redaction_does_not_overreach_into_ordinary_words():
    """verbatim-index redacted the contraction "that\'s" 34 times chasing a surname."""
    from modules.consensus.dossier import redact_name
    out = redact_name(
        "Ada Vance was ranked; advance bookings rose and the balance held.",
        "Ada Vance",
    )
    assert "[SUBJECT] was ranked" in out
    assert "advance bookings" in out, "a substring match would have eaten 'advance'"
    assert "balance held" in out
    # short tokens are not redacted alone
    assert redact_name("An ad ran.", "Ada Vance") == "An ad ran."


def test_shuffling_changes_only_the_order_not_the_evidence():
    obs = [_rank_obs(f"obs_{i}", "le_1", 10 + i) for i in range(5)]
    a = build_dossier("p_1", "Ada", "2010", obs, EDITIONS)
    b = build_dossier("p_1", "Ada", "2010", obs, EDITIONS, shuffle_seed=7)
    assert set(a.observation_ids) == set(b.observation_ids)
    assert a.text != b.text or a.observation_ids == b.observation_ids


# -- syndication ------------------------------------------------------------

def test_five_copies_of_one_list_collapse_to_one_observation():
    copies = [
        _rank_obs(f"obs_{i}", "le_1", 12, original="le_canonical", syndicated=i > 0)
        for i in range(5)
    ]
    kept, dropped = collapse_syndication(copies)
    assert len(kept) == 1 and dropped == 4
    assert kept[0].lineage.is_syndicated_copy is False, "the canonical copy survives"


def test_copy_volume_does_not_raise_independence_in_the_dossier():
    one = [_rank_obs("obs_0", "le_1", 12, original="le_canonical")]
    many = one + [
        _rank_obs(f"obs_{i}", "le_1", 12, original="le_canonical", syndicated=True)
        for i in range(1, 5)
    ]
    d_one = build_dossier("p_1", "Ada", "2010", one, EDITIONS)
    d_many = build_dossier("p_1", "Ada", "2010", many, EDITIONS)
    assert d_one.distinct_original_sources == d_many.distinct_original_sources == 1
    assert d_one.text == d_many.text, "the judge sees identical bytes"
    assert d_many.syndicated_copies_dropped == 4


def test_two_genuinely_different_publishers_do_count_as_two():
    obs = [
        _rank_obs("obs_1", "le_1", 12, original="le_1"),
        _rank_obs("obs_2", "le_2", 50, original="le_2"),
    ]
    d = build_dossier("p_1", "Ada", "2010", obs, EDITIONS)
    assert d.distinct_original_sources == 2 and d.distinct_publishers == 2


# -- empty dossiers ---------------------------------------------------------

def test_an_empty_dossier_says_return_unscored_and_never_implies_a_low_score():
    d = build_dossier("p_1", "Ada Vance", "2016", [], EDITIONS)
    assert d.is_empty
    assert "Return unscored" in d.text
    lowered = d.text.lower()
    for forbidden in ("low score", "not attractive", "unattractive",
                      "score of 0", "rate them low", "below average"):
        assert forbidden not in lowered, f"an empty dossier must not steer low: {forbidden!r}"


# -- rendering keeps source-local facts source-local ------------------------

def test_a_publication_rating_is_rendered_as_that_publications_number():
    o = Observation(
        observation_id="obs_r", person_id="p_1", list_edition_id="le_1",
        evidence_type=EvidenceType.PUBLICATION_RATING,
        observed={"rating_value": 8, "rating_scale": "1-10"},
        concerns_period=_pd("2010"), published_at=_pd("2010"),
        lineage=Lineage(original_source="le_1"),
        excerpt="Hotness: 8/10", excerpt_locator="entry 4",
    )
    d = build_dossier("p_1", "Ada", "2010", [o], EDITIONS)
    assert "their number" in d.text
    assert "not a score you are being asked to reproduce" in d.text


def test_an_unordered_inclusion_is_rendered_without_implying_a_position():
    o = Observation(
        observation_id="obs_u", person_id="p_1", list_edition_id="le_1",
        evidence_type=EvidenceType.UNORDERED_INCLUSION,
        observed={"list_length": 15},
        concerns_period=_pd("2008"), published_at=_pd("2008-11-18", Precision.DAY),
        lineage=Lineage(original_source="le_1"),
        excerpt="Ada Vance", excerpt_locator="gallery item 4 of 15",
    )
    d = build_dossier("p_1", "Ada", "2008", [o], EDITIONS)
    assert "does not state an order, so no position is implied" in d.text
    assert "4 of 15" not in d.text.split("quoted:")[0], "gallery position is not a rank"


def test_retrospective_items_are_marked_as_such_to_the_judge():
    o = Observation(
        observation_id="obs_ret", person_id="p_1", list_edition_id="le_1",
        evidence_type=EvidenceType.QUALITATIVE_COMMENTARY, observed={},
        concerns_period=_pd("1995"), published_at=_pd("2018"),
        lineage=Lineage(original_source="le_1"),
        excerpt="looking back, the defining face of the decade",
        excerpt_locator="paragraph 6", retrospective=True,
    )
    d = build_dossier("p_1", "Ada", "1995", [o], EDITIONS)
    assert "RETROSPECTIVE" in d.text


def test_the_pool_a_source_drew_from_always_reaches_the_judge():
    d = build_dossier("p_1", "Ada", "2010", [_rank_obs("obs_1", "le_1", 12)], EDITIONS)
    assert "pool the source drew from: people in English-language film" in d.text


def test_an_unstated_list_size_does_not_render_as_zero_names():
    o = Observation(
        observation_id="obs_u2", person_id="p_1", list_edition_id="le_1",
        evidence_type=EvidenceType.UNORDERED_INCLUSION,
        observed={"list_length": None},
        concerns_period=_pd("2004"), published_at=_pd("2004"),
        lineage=Lineage(original_source="le_1"),
        excerpt="named one of the most beautiful women of all time",
        excerpt_locator="article prose",
    )
    text = build_dossier("p_1", "Ada", "2004", [o], EDITIONS).text
    assert "a set of 0 names" not in text
    assert "a set whose size the source does not state" in text


def test_qualitative_commentary_points_the_judge_at_the_quote():
    o = Observation(
        observation_id="obs_q", person_id="p_1", list_edition_id="le_1",
        evidence_type=EvidenceType.QUALITATIVE_COMMENTARY, observed={},
        concerns_period=_pd("2012"), published_at=_pd("2012"),
        lineage=Lineage(original_source="le_1"),
        excerpt="the most beautiful face in the room", excerpt_locator="paragraph 3",
    )
    text = build_dossier("p_1", "Ada", "2012", [o], EDITIONS).text
    assert "the quoted text below is the whole of the judgment" in text.lower()
    assert "the most beautiful face in the room" in text


def test_a_rank_with_no_stated_depth_says_so_rather_than_implying_one():
    o = Observation(
        observation_id="obs_r2", person_id="p_1", list_edition_id="le_1",
        evidence_type=EvidenceType.ORDERED_RANK,
        observed={"rank": 1, "list_length": None, "order_is_ranking": True,
                  "order_basis": "the article says she topped the ranking"},
        concerns_period=_pd("2004"), published_at=_pd("2004"),
        lineage=Lineage(original_source="le_1"),
        excerpt="topping the ranking in 2004", excerpt_locator="prose",
    )
    text = build_dossier("p_1", "Ada", "2004", [o], EDITIONS).text
    assert "of 100" not in text
    assert "does not state how long the list was" in text


# -- what redaction deliberately leaves behind -------------------------------

def test_short_name_tokens_survive_redaction_and_are_reported():
    """MIN_TOKEN_LEN = 4 is a deliberate tradeoff: redacting "de" or "Ben"
    everywhere would mangle ordinary prose. The cost is that a first name
    shorter than four characters survives, and seven of the 37 names in this
    project's own cohort and partner universe have one -- Ben, Ana, Liv, Len.

    The identity-leakage probe currently uses synthetic names whose tokens are
    all long enough, so it is unaffected. Run it on Ben Affleck and it would
    report "no leakage" while the judge had read "Ben". A probe that cannot see
    its own blind spot reports a clean result either way, so the blind spot is
    now returned rather than assumed away.
    """
    from modules.consensus.dossier import residual_identity_tokens
    text = "Ben went to the ceremony. [SUBJECT] was named."
    assert residual_identity_tokens(text, "Ben Affleck") == ("Ben",)


def test_a_fully_redacted_text_reports_nothing_residual():
    from modules.consensus.dossier import redact_name, residual_identity_tokens
    text = redact_name("Ada Vance placed 12th.", "Ada Vance")
    assert residual_identity_tokens(text, "Ada Vance") == ()


def test_the_full_name_is_still_redacted_even_when_a_token_is_short():
    """Longest-first matching means "Ben Affleck" goes before any token rule,
    so the common case is covered. Only a BARE short token survives."""
    from modules.consensus.dossier import redact_name
    out = redact_name("Ben Affleck — Sexiest Man Alive 1997", "Ben Affleck")
    assert "Affleck" not in out and "Ben Affleck" not in out
    assert out.startswith("[SUBJECT]")


def test_residual_detection_ignores_case_and_word_boundaries():
    from modules.consensus.dossier import residual_identity_tokens
    assert residual_identity_tokens("BEN arrived", "Ben Affleck") == ("Ben",)
    assert residual_identity_tokens("Benjamin arrived", "Ben Affleck") == ()


def _obs_with(excerpt):
    return Observation(
        observation_id="obs_r", person_id="p_1", list_edition_id="le_1",
        evidence_type=EvidenceType.ORDERED_RANK,
        observed={"rank": 12, "list_length": 50, "order_is_ranking": True,
                  "order_basis": "page reads 'The Results'"},
        concerns_period=_pd("1997"), published_at=_pd("1997-08-17", Precision.DAY),
        lineage=Lineage(original_source="le_1", is_syndicated_copy=False),
        excerpt=excerpt, excerpt_locator="slide 39 of 50",
    )


def test_an_anonymised_dossier_reports_what_redaction_could_not_remove():
    """A leakage probe that cannot see its own blind spot reports clean either
    way. The dossier now carries the blind spot."""
    d = build_dossier("Q1", "Ben Affleck", "1997",
                      [_obs_with("Ben placed 12th.")], EDITIONS, anonymise=True)
    assert d.residual_name_tokens == ("Ben",), d.text
    assert "Affleck" not in d.text, "the full name must still be gone"


def test_a_name_with_no_short_tokens_reports_nothing_residual():
    d = build_dossier("Q1", "Jordan Quill", "1997",
                      [_obs_with("Jordan Quill placed 12th.")], EDITIONS,
                      anonymise=True)
    assert d.residual_name_tokens == ()


def test_a_named_dossier_reports_nothing_residual():
    """Residual tokens only mean something when anonymisation was requested."""
    d = build_dossier("Q1", "Ben Affleck", "1997",
                      [_obs_with("Ben placed 12th.")], EDITIONS, anonymise=False)
    assert d.residual_name_tokens == ()
