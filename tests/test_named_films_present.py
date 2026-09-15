"""The operator's own acceptance test, kept so it cannot quietly regress.

"I should not be able to click on any one person and say why is this actress or
actor missing." Five films were named as glaring omissions, and they had two
separate causes.

Three of them -- Gigli, Armageddon, Ghosted -- had BOTH actors on the 100-name
roster all along. They were missing because `fetch_onscreen_candidates.py` ran
one SPARQL query with `LIMIT 400` against a roster that produces 2570 rows, so
Wikidata returned the first 400 and dropped the rest in silence. 25 of the 100
roster members had no co-starring pair at all.

The other two -- 50 First Dates, Good Will Hunting -- were missing because Drew
Barrymore and Minnie Driver are not on the 100-name roster, and a closed set
cannot be queried into containing somebody. They need the expanded roster from
`scripts/expand_roster.py`.

`data/` is gitignored, so each half skips when its artifact is absent rather
than failing on a fresh clone. Nothing here touches the network.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

#: title -> (male, female). Both actors are on the 100-name roster.
ON_THE_HUNDRED = {
    "Gigli": ("Ben Affleck", "Jennifer Lopez"),
    "Armageddon": ("Ben Affleck", "Liv Tyler"),
    "Ghosted": ("Chris Evans", "Ana de Armas"),
}

#: title -> (male, female). The woman reaches the roster only by expansion.
NEEDS_EXPANSION = {
    "50 First Dates": ("Adam Sandler", "Drew Barrymore"),
    "Good Will Hunting": ("Matt Damon", "Minnie Driver"),
}

#: All five the operator named.
ALL_FIVE = {**ON_THE_HUNDRED, **NEEDS_EXPANSION}


def _pairs(relative: str):
    path = REPO / relative
    if not path.exists():
        pytest.skip(f"data/ is gitignored; run the fetcher to make {relative}")
    return json.loads(path.read_text())["candidates"]


def _present(pairs, title, male, female) -> bool:
    return any(p["title"] == title and p["male"] == male and p["female"] == female
               for p in pairs)


@pytest.mark.parametrize("title", sorted(ON_THE_HUNDRED))
def test_the_hundred_name_roster_finds_the_films_whose_actors_are_both_on_it(title):
    """These three were lost to a LIMIT, not to a gap in Wikidata."""
    male, female = ON_THE_HUNDRED[title]
    pairs = _pairs("data/roster100/records/onscreen_candidates.json")
    assert _present(pairs, title, male, female), (
        f"{title} ({male} + {female}) is missing from the 100-name roster's "
        f"candidates, which hold {len(pairs)} pairs. Both actors are on "
        "docs/roster-100.json, so this is the truncation defect returning.")


@pytest.mark.parametrize("title", sorted(ALL_FIVE))
def test_the_expanded_roster_finds_all_five_named_films(title):
    male, female = ALL_FIVE[title]
    pairs = _pairs("data/rosterexp/records/onscreen_candidates.json")
    assert _present(pairs, title, male, female), (
        f"{title} ({male} + {female}) is missing from the expanded roster's "
        f"candidates, which hold {len(pairs)} pairs.")


def test_no_roster_member_is_invisible_in_the_hundred_name_candidates():
    """25 of the 100 had ZERO co-starring pairs before the LIMIT was fixed,
    Julia Roberts and Leonardo DiCaprio among them. A person with no pair is a
    person a reader can click and find nothing behind."""
    pairs = _pairs("data/roster100/records/onscreen_candidates.json")
    roster = json.loads((REPO / "docs/roster-100.json").read_text())["people"]
    covered = {p["male_qid"] for p in pairs} | {p["female_qid"] for p in pairs}
    invisible = sorted(p["display_name"] for p in roster
                       if p["wikidata_qid"] not in covered)
    assert invisible == [], f"roster members with no co-starring pair: {invisible}"
