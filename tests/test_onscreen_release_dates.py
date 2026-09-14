"""A film's release date must be recorded at the precision the source states.

`packages/temporal/dates.py` exists to stop a year becoming a day, and the
project's own test list names "Year-precision date: never becomes January 1".
The on-screen fetcher bypassed all of it: it took `wdt:P577` and sliced the
literal to ten characters, so a year-precision statement -- which Wikidata
serialises as `+2002-01-01T00:00:00Z` with precision 9 -- was stored as
`2002-01-01`. Eleven of the pilot's twenty films carried that invented
January 1st.

The second half of the problem is that P577 REPEATS, once per country. The old
code kept whichever SPARQL row arrived first. These tests pin the replacement
rule, which is the part most likely to be quietly changed later.

No test here touches the network.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

YEAR, MONTH, DAY = 9, 10, 11


def _mod():
    spec = importlib.util.spec_from_file_location(
        "fetch_onscreen_candidates", REPO / "scripts/fetch_onscreen_candidates.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


# --------------------------------------------------------------------------
# format_release
# --------------------------------------------------------------------------

def test_a_year_precision_date_never_becomes_january_first():
    """The whole reason this file exists."""
    assert _mod().format_release("2002-01-01T00:00:00Z", YEAR) == "2002"


def test_a_year_precision_date_with_zero_month_and_day_is_also_a_year():
    """Wikidata writes year precision both ways: 1998-01-01 and 1998-00-00."""
    assert _mod().format_release("1998-00-00T00:00:00Z", YEAR) == "1998"


def test_a_day_precision_date_keeps_its_day():
    assert _mod().format_release("2003-02-09T00:00:00Z", DAY) == "2003-02-09"


def test_a_month_precision_date_keeps_its_month_and_no_day():
    assert _mod().format_release("2003-02-01T00:00:00Z", MONTH) == "2003-02"


def test_a_precision_coarser_than_a_year_is_not_promoted():
    """Decade precision must not be rendered as if it were a year we know."""
    assert _mod().format_release("1990-01-01T00:00:00Z", 8) == "1990"


# --------------------------------------------------------------------------
# choose_release
# --------------------------------------------------------------------------

def test_nothing_to_choose_from_returns_none():
    """A film with no publication date gets no date, not a guessed one."""
    assert _mod().choose_release([]) is None


def test_a_year_statement_beats_the_country_releases():
    """Deconstructing Harry: year 1997, plus a 1998 foreign release.

    The film opened in December 1997. Taking the finest available date would
    have moved it into the wrong YEAR, and the year is what every consumer
    reads.
    """
    got = _mod().choose_release([("1997-01-01T00:00:00Z", YEAR),
                                 ("1998-05-21T00:00:00Z", DAY)])
    assert got[1] == YEAR and got[0].startswith("1997")


def test_with_no_year_statement_the_majority_year_wins():
    """Thor: Love and Thunder carries two 2021 dates against six in 2022.

    Earliest-wins was tried first and moved a 2022 film to 2021. A majority
    over the source's own repeated statements survives a stray value.
    """
    vals = [("2021-10-28T00:00:00Z", DAY), ("2021-11-05T00:00:00Z", DAY)] + [
        (f"2022-0{i}-01T00:00:00Z", DAY) for i in range(2, 8)]
    got = _mod().choose_release(vals)
    assert got[0][:4] == "2022"


def test_the_earliest_date_within_the_chosen_year_is_taken():
    vals = [("2003-03-20T00:00:00Z", DAY), ("2003-02-09T00:00:00Z", DAY),
            ("2003-02-14T00:00:00Z", DAY)]
    assert _mod().choose_release(vals)[0].startswith("2003-02-09")


def test_a_tie_between_years_goes_to_the_earlier_one():
    """Jersey Girl: one 2004 date and one 2005 date.

    Some rule has to break the tie, and it must not be iteration order.
    """
    m = _mod()
    a = ("2004-03-09T00:00:00Z", DAY)
    b = ("2005-01-06T00:00:00Z", DAY)
    assert m.choose_release([a, b])[0][:4] == "2004"
    assert m.choose_release([b, a])[0][:4] == "2004", "order must not matter"


def test_a_single_date_is_returned_unchanged():
    got = _mod().choose_release([("2022-03-18T00:00:00Z", DAY)])
    assert got[0].startswith("2022-03-18") and got[1] == DAY


# --------------------------------------------------------------------------
# the artifact this repo currently has
# --------------------------------------------------------------------------

def test_no_stored_release_is_an_invented_january_first():
    import json
    path = REPO / "data/pilot/records/onscreen_candidates.json"
    if not path.exists():
        pytest.skip("data/ is gitignored; run scripts/fetch_onscreen_candidates.py")
    rows = json.loads(path.read_text())["candidates"]
    bad = [(r["title"], r["release"]) for r in rows
           if r["release"].endswith("-01-01") and r.get("release_precision") != "day"]
    assert bad == [], f"year-precision dates stored as January 1: {bad}"


def test_every_stored_release_matches_its_declared_precision():
    import json
    path = REPO / "data/pilot/records/onscreen_candidates.json"
    if not path.exists():
        pytest.skip("data/ is gitignored")
    width = {"year": 4, "month": 7, "day": 10}
    for r in json.loads(path.read_text())["candidates"]:
        prec = r.get("release_precision")
        if prec is None:
            assert r["release"] == ""
            continue
        assert len(r["release"]) == width[prec], (
            f"{r['title']} declares {prec} precision but stores {r['release']!r}")


# --------------------------------------------------------------------------
# the class of bug, not just this instance
# --------------------------------------------------------------------------

#: Wikidata time-valued properties this project reads or might read.
DATE_PROPERTIES = ("P569", "P570", "P577", "P580", "P582", "P585")


def test_no_query_fetches_a_date_through_the_bare_wdt_path():
    """`wdt:` returns a time with no precision, and that is the whole bug.

    Every other query in this repository already uses the statement path --
    `psv:P569 [ wikibase:timePrecision ?prec ]` -- and reads the precision.
    `fetch_onscreen_candidates.py` used `wdt:P577` and eleven of twenty films
    got an invented January 1st.

    This fails on the PATTERN rather than on the one file, because the next
    date property someone adds will be written the same easy way. A `wdt:`
    path is right for a Q-id and wrong for a time.
    """
    import re
    offenders = []
    for path in sorted((REPO / "scripts").glob("*.py")) + \
            sorted((REPO / "modules").rglob("*.py")):
        text = path.read_text()
        for prop in DATE_PROPERTIES:
            for m in re.finditer(rf"wdt:{prop}\b", text):
                line = text[: m.start()].count("\n") + 1
                # A mention inside a comment or docstring is explanation, not a
                # query. Only flag it where it is part of SPARQL.
                stmt = text.splitlines()[line - 1].strip()
                if stmt.startswith("#") or stmt.startswith("The old code"):
                    continue
                offenders.append(f"{path.relative_to(REPO)}:{line} {stmt[:70]}")
    assert offenders == [], (
        "these fetch a time-valued property through wdt:, which drops the "
        "precision and turns a year into January 1:\n  " + "\n  ".join(offenders)
    )
