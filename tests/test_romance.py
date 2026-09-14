from __future__ import annotations

import json

import pytest

from modules.records.romance import QUALIFYING, RomanceVerdict, parse_verdict

PLOT = (
    "Rafe and Evelyn meet at a medical examination and begin a courtship. "
    "Rafe volunteers for the Eagle Squadron and is reported killed. Evelyn and "
    "Danny grow close and become involved. Rafe returns alive."
)


def _reply(**over):
    body = {"schema_version": "romance-1.0", "work": "Example Film",
            "classification": "reciprocal_romance",
            "evidence": "Rafe and Evelyn meet at a medical examination and begin a courtship.",
            "reasoning": "The plot describes a mutual courtship.",
            "characters": {"a": "Rafe", "b": "Evelyn"}}
    body.update(over)
    return json.dumps(body)


def test_a_grounded_reciprocal_romance_qualifies():
    v = parse_verdict(_reply(), "Example Film", PLOT, "sha")
    assert v.classification == QUALIFYING
    assert v.grounded is True and v.qualifies is True


def test_co_appearance_is_the_default_and_does_not_qualify():
    v = parse_verdict(
        _reply(classification="co_appearance_only",
               evidence="Rafe returns alive.",
               reasoning="No romantic link between these two characters."),
        "Example Film", PLOT, "sha")
    assert v.qualifies is False


def test_an_ungrounded_quote_cannot_support_a_romance_classification():
    """The only classification that puts a couple on a board needs real evidence."""
    v = parse_verdict(
        _reply(evidence="They marry in the final scene and live happily."),
        "Example Film", PLOT, "sha")
    assert v.grounded is False
    assert v.classification == "cannot_tell", "downgraded, not accepted"
    assert v.qualifies is False


def test_an_ungrounded_quote_on_a_non_qualifying_class_is_kept_but_flagged():
    v = parse_verdict(
        _reply(classification="family_or_platonic", evidence="They are siblings."),
        "Example Film", PLOT, "sha")
    assert v.classification == "family_or_platonic"
    assert v.grounded is False


def test_whitespace_differences_do_not_break_grounding():
    v = parse_verdict(
        _reply(evidence="Rafe  and\nEvelyn   meet at a medical examination"),
        "Example Film", PLOT, "sha")
    assert v.grounded is True


def test_unrequited_and_incidental_do_not_qualify():
    for c in ("unrequited", "brief_or_incidental", "cannot_tell"):
        v = parse_verdict(_reply(classification=c, evidence="Rafe returns alive."),
                          "Example Film", PLOT, "sha")
        assert v.qualifies is False, c


def test_coercion_is_never_scored_as_a_romantic_pairing():
    v = parse_verdict(
        _reply(classification="coerced_or_assault", evidence="Rafe returns alive."),
        "Example Film", PLOT, "sha")
    assert v.qualifies is False
    assert v.classification == "coerced_or_assault", "recorded, not silently dropped"


def test_an_unknown_classification_is_refused():
    with pytest.raises(ValueError, match="unknown classification"):
        parse_verdict(_reply(classification="probably_yes"), "F", PLOT, "sha")


def test_a_wrong_schema_version_is_refused():
    with pytest.raises(ValueError, match="schema_version"):
        parse_verdict(_reply(schema_version="romance-0.9"), "F", PLOT, "sha")


def test_empty_evidence_is_never_grounded():
    v = parse_verdict(_reply(evidence=""), "F", PLOT, "sha")
    assert v.grounded is False and v.classification == "cannot_tell"


def test_the_candidate_records_carry_a_qid_so_the_article_need_not_be_guessed():
    """Measured 2026-09-14: fetching by film title sent 13 of 20 candidates to
    the wrong Wikipedia article and reported 'no Plot section' for each. Pearl
    Harbor is a harbour, Elektra is a Greek tragedy, Daredevil is a comic. Each
    returned a real article with no plot, which is indistinguishable from a
    genuinely missing plot. The fix is to resolve the sitelink from the film's
    Wikidata id, which cannot land on a different subject."""
    import json
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    blob = json.loads(
        (repo / "data/pilot/records/onscreen_candidates.json").read_text())
    for c in blob["candidates"]:
        assert c["work_qid"].startswith("Q"), (
            "every on-screen candidate must carry a Wikidata id, or the article "
            "has to be guessed from an ambiguous title"
        )
