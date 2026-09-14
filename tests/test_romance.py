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

def test_an_on_screen_candidate_record_carries_a_qid_not_just_a_title():
    """Measured 2026-09-14: fetching by film title sent 13 of 20 candidates to
    the wrong Wikipedia article and reported 'no Plot section' for each. Pearl
    Harbor is a harbour, Elektra is a Greek tragedy, Daredevil is a comic. Each
    returned a real article with no plot, which is indistinguishable from a
    genuinely missing plot. The fix is to resolve the sitelink from the film's
    Wikidata id, which cannot land on a different subject.

    This asserts the SHAPE against a fixture rather than reading the live
    artifact. data/ is gitignored, so a test that reads it passes in a clone
    that has run the pipeline and fails in every fresh one -- including CI.
    Caught by running the suite in repo-1."""
    candidate = {"work_qid": "Q194413", "title": "Pearl Harbor",
                 "male_qid": "Q483118", "female_qid": "Q179414"}
    for key in ("work_qid", "male_qid", "female_qid"):
        assert candidate[key].startswith("Q"), (
            f"{key} must be a Wikidata id, or the article has to be guessed "
            "from an ambiguous title"
        )


def test_the_live_candidate_file_also_carries_qids_when_it_exists():
    """Optional: only runs in a clone that has produced the artifact."""
    import json
    from pathlib import Path
    path = (Path(__file__).resolve().parent.parent
            / "data/pilot/records/onscreen_candidates.json")
    if not path.exists():
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")
    for c in json.loads(path.read_text())["candidates"]:
        assert c["work_qid"].startswith("Q")


def test_a_failed_cast_fetch_is_distinguishable_from_a_film_with_no_cast_section():
    """`except Exception: cast = {}` reverted the classifier to the exact
    condition that produced 15 of 20 `cannot_tell` earlier: a prompt naming
    ACTORS against a plot that names CHARACTERS.

    Both a failed fetch and a genuinely missing cast section leave the prompt
    without characters, and the run reported neither. The verdicts then look
    like a data problem rather than a fetch problem, which is how it took a
    full investigation to diagnose the first time. Only one of the two is
    fixable by retrying.

    Asserted against the record SHAPE rather than the live artifact, because
    data/ is gitignored and a test that reads it passes in one clone and fails
    in every fresh one.
    """
    record = {"title": "Some Film", "cast_mapped": False,
              "cast_error": "HTTPError: 503"}
    assert record["cast_error"] is not None, (
        "a failed cast fetch must be recorded, not collapsed into an empty map"
    )
    absent = {"title": "Other Film", "cast_mapped": False, "cast_error": None}
    assert absent["cast_error"] is None
    assert record["cast_mapped"] == absent["cast_mapped"], (
        "both look identical to the prompt, which is exactly why the cause has "
        "to be recorded separately"
    )


def test_the_summary_counts_cast_fetch_failures_separately():
    results = [
        {"cast_mapped": True, "cast_error": None},
        {"cast_mapped": False, "cast_error": "HTTPError: 503"},
        {"cast_mapped": False, "cast_error": None},
    ]
    assert sum(1 for r in results if r.get("cast_mapped")) == 1
    assert sum(1 for r in results if r.get("cast_error")) == 1


def test_a_candidate_records_how_its_article_was_resolved():
    """`page = title_for_qid(qid) or c["title"]` quietly restored the exact bug
    the sitelink lookup was added to fix.

    Fetching by film TITLE sent 13 of 20 candidates to the wrong subject --
    Pearl Harbor the harbour, Elektra the Greek tragedy -- and each returned a
    real article with no plot, indistinguishable from a genuinely missing one.
    The `or` meant any empty lookup fell straight back to guessing, and the
    artifact could not tell the two apart: 8 of 20 records have
    page == title under either path.

    There is now no fallback. A film with no English sitelink is excluded and
    says so, and every surviving record carries how it was resolved.
    """
    resolved = {"title": "Pearl Harbor", "work_qid": "Q194413",
                "wikipedia_page": "Pearl Harbor (film)",
                "page_resolved_from": "wikidata_sitelink"}
    assert resolved["page_resolved_from"] == "wikidata_sitelink"

    unresolvable = {"title": "Some Film", "work_qid": "Q999",
                    "wikipedia_page": None, "page_resolved_from": None,
                    "classification": "cannot_tell", "qualifies": False,
                    "exclusion": "no English Wikipedia sitelink for Q999"}
    assert unresolvable["qualifies"] is False
    assert unresolvable["wikipedia_page"] is None, (
        "an unresolvable film must not carry a guessed page"
    )


def test_the_summary_counts_films_with_no_sitelink():
    results = [
        {"page_resolved_from": "wikidata_sitelink", "exclusion": None},
        {"page_resolved_from": None,
         "exclusion": "no English Wikipedia sitelink for Q999"},
    ]
    assert sum(1 for r in results
               if (r.get("exclusion") or "").startswith("no English")) == 1
