"""The two independent supports for a relationship claim, cross-tabulated.

`docs/RELATIONSHIP-REVIEW.md` tells a reader that the claims with no Wikidata
reference are the ones most likely to be wrong. It then left them to check all
of those by hand. Whether Wikipedia's prose corroborates a claim is independent
of whether Wikidata cites a source -- different editors wrote each -- so the
two together name the claims with nothing behind them at all.

Today that list is empty, which is why it has to be tested with a fixture: the
branch that reports an unsupported claim has never run against real data, and
a branch that has never run is exactly what this project keeps finding broken.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "relationship_review", REPO / "scripts/relationship_review.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _row(eid, subject, partner, has_reference):
    return {"episode_id": eid, "subject": subject, "partner": partner,
            "has_reference": has_reference}


def _corr(eid, subject, partner, verdict):
    return {(eid, subject, partner): {
        "episode_id": eid, "subject": subject, "partner": partner,
        "verdict": verdict}}


def test_a_referenced_claim_is_not_in_the_unreferenced_set():
    m = _mod()
    rows = [_row("e1", "A", "B", True)]
    unref, rescued, naked = m.unreferenced_support(rows, _corr("e1", "A", "B", "not_mentioned"))
    assert unref == [] and rescued == 0 and naked == []


def test_an_unreferenced_claim_the_prose_confirms_is_counted_as_rescued():
    m = _mod()
    rows = [_row("e1", "A", "B", False)]
    unref, rescued, naked = m.unreferenced_support(
        rows, _corr("e1", "A", "B", "prose_confirms_a_stored_year"))
    assert len(unref) == 1 and rescued == 1 and naked == []


def test_an_unreferenced_claim_named_in_neither_article_is_reported():
    """The branch that has never run against real data."""
    m = _mod()
    rows = [_row("e1", "A", "B", False)]
    unref, rescued, naked = m.unreferenced_support(
        rows, _corr("e1", "A", "B", "not_mentioned"))
    assert rescued == 0
    assert [(c["subject"], c["partner"]) for c in naked] == [("A", "B")]


def test_a_claim_with_no_stored_date_is_neither_rescued_nor_naked():
    """There is nothing to corroborate, so it is not evidence either way."""
    m = _mod()
    rows = [_row("e1", "A", "B", False)]
    unref, rescued, naked = m.unreferenced_support(
        rows, _corr("e1", "A", "B", "no_stored_date"))
    assert len(unref) == 1 and rescued == 0 and naked == []


def test_an_unreferenced_claim_with_no_corroboration_row_is_not_called_naked():
    """Absent from the corroboration run is not the same as absent from the
    articles. Calling it unsupported would manufacture a finding out of a
    stage that simply has not run."""
    m = _mod()
    unref, rescued, naked = m.unreferenced_support([_row("e1", "A", "B", False)], {})
    assert len(unref) == 1 and rescued == 0 and naked == []


def test_the_naked_list_is_ordered_independently_of_input():
    m = _mod()
    rows = [_row("e2", "Z", "Y", False), _row("e1", "A", "B", False)]
    corr = {**_corr("e2", "Z", "Y", "not_mentioned"),
            **_corr("e1", "A", "B", "not_mentioned")}
    naked = m.unreferenced_support(rows, corr)[2]
    assert [c["subject"] for c in naked] == ["A", "Z"]
    naked2 = m.unreferenced_support(list(reversed(rows)), corr)[2]
    assert [c["subject"] for c in naked2] == ["A", "Z"], "order must not matter"


def test_the_sheet_currently_reports_nothing_unsupported():
    """If this starts failing, a relationship claim has lost both supports and
    the review sheet's opening advice changes."""
    doc = REPO / "docs/RELATIONSHIP-REVIEW.md"
    if not doc.exists():
        pytest.skip("data/ is gitignored; run the chain first")
    text = doc.read_text()
    if "unreferenced claims" not in text:
        pytest.skip("corroboration has not been run for this sheet")
    assert "is missing from both" in text, (
        "the sheet no longer says every claim has something behind it; read it")
