"""Corroboration must not read as verification.

`scripts/corroborate_relationships.py` puts Wikipedia's own sentences beside
Wikidata's dates so a reviewer stops looking up 31 claims by hand. The risk is
not that it misses something. It is that a label gets mistaken for a result:
the first version called the mismatch bucket `years_differ`, and all four
episodes it selected turned out to have CORRECT dates in sentences that carried
another year for another reason.

So these tests pin the classifier's meaning, and pin that a surname-only match
is reported as a surname-only match rather than silently treated as the person.

No test here touches the network.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "corroborate_relationships", REPO / "scripts/corroborate_relationships.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _ep(start=None, end=None):
    ep = {}
    if start:
        ep["start"] = {"value": start, "precision": "year"}
    if end:
        ep["end"] = {"value": end, "precision": "year"}
    return ep


# --------------------------------------------------------------------------
# sentence selection
# --------------------------------------------------------------------------

def test_a_full_name_match_is_reported_as_one():
    m = _mod()
    hits, how = m.sentences_naming(
        "Ford began dating Calista Flockhart in 2002. He left.", "Calista Flockhart")
    assert how == "full name" and len(hits) == 1


def test_a_surname_only_match_is_labelled_as_such():
    """"Hudson" in Kate Hudson's article may be Goldie Hawn's son.

    Reporting WHICH form matched lets the reader weigh it. Silently treating a
    surname hit as the person is what would make the whole sheet untrustworthy.
    """
    m = _mod()
    hits, how = m.sentences_naming("She married Wiseman in 2004.", "Len Wiseman")
    assert how == "surname only" and len(hits) == 1


def test_a_short_surname_does_not_fall_back():
    """A three-letter surname matches far too much prose to be evidence."""
    m = _mod()
    hits, how = m.sentences_naming("They met at the bar in 1999.", "Someone Bar")
    assert how == "none" and hits == []


def test_no_mention_returns_nothing():
    m = _mod()
    hits, how = m.sentences_naming("An article about somebody else.", "Shauna Sexton")
    assert hits == [] and how == "none"


def test_sentences_are_split_on_terminators_not_newlines():
    m = _mod()
    hits, _ = m.sentences_naming(
        "First thing. Ford married Calista Flockhart. Third thing.",
        "Calista Flockhart")
    assert hits == ["Ford married Calista Flockhart."]


# --------------------------------------------------------------------------
# years
# --------------------------------------------------------------------------

def test_years_are_read_from_the_sentences():
    assert _mod().years_in(["Met in 1995 and married in 2004."]) == {1995, 2004}


def test_a_number_that_is_not_a_year_is_ignored():
    """Ages, box office and runtimes are not years."""
    assert _mod().years_in(["He was 45 and it made 300 million."]) == set()


def test_stored_years_take_the_year_off_any_precision():
    m = _mod()
    assert m.stored_years({"start": {"value": "2020-03"}, "end": {"value": "2021-01"}}) \
        == {2020, 2021}
    assert m.stored_years({"start": {"value": "1998"}}) == {1998}


# --------------------------------------------------------------------------
# the labels, which are the part that can mislead
# --------------------------------------------------------------------------

def test_an_overlapping_year_is_corroboration():
    m = _mod()
    assert m.classify(["They married in 2004."], _ep("2004", "2019")) \
        == "prose_confirms_a_stored_year"


def test_a_non_overlapping_year_is_not_called_a_disagreement():
    """The real Harrison Ford case: prose says 2002, stored says 2010.

    Both are right -- they met in 2002 and married in 2010. The label must not
    assert that anything is wrong, because on the first real run all four
    episodes in this bucket had correct dates.
    """
    m = _mod()
    verdict = m.classify(
        ["Ford began dating Calista Flockhart after they met at the 2002 "
         "Golden Globe Awards."], _ep("2010"))
    assert verdict == "prose_names_other_years"
    assert "differ" not in verdict and "wrong" not in verdict


def test_no_mention_is_its_own_label():
    assert _mod().classify([], _ep("2018")) == "not_mentioned"


def test_a_mention_with_no_year_is_its_own_label():
    m = _mod()
    assert m.classify(["He is married to actress Calista Flockhart."], _ep("2010")) \
        == "mentioned_no_year"


def test_an_episode_with_no_stored_date_is_not_judged():
    """Two pilot episodes have no start date at all. There is nothing to
    corroborate, and calling that a mismatch would invent a disagreement."""
    m = _mod()
    assert m.classify(["They married in 2019."], {}) == "no_stored_date"


# --------------------------------------------------------------------------
# the artifact this repo currently has
# --------------------------------------------------------------------------

def test_the_recorded_run_is_self_consistent():
    import json
    path = REPO / "data/pilot/records/relationship_corroboration.json"
    if not path.exists():
        pytest.skip("data/ is gitignored; run scripts/corroborate_relationships.py")
    d = json.loads(path.read_text())
    assert sum(d["verdict_counts"].values()) == d["episodes_checked"] == len(d["rows"])
    assert "not a finding" in d["note"], (
        "the artifact must carry the warning that these labels are not verdicts")
