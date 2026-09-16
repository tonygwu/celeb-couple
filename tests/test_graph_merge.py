"""The same romance from two graphs is ONE romance.

The IMDb graph names a film by its tconst and the Wikidata graph names the same
film by its QID, so the two carry different `pairing_id`s for the same event.
Deduping on pairing_id therefore missed them entirely, and Adam Sandler's row
showed Just Go with It, Murder Mystery and Murder Mystery 2 twice each. His
romance count read 7 where the truth is 4, and cumulative double-counted.
"""
from __future__ import annotations

import pytest

from modules.pairing.merge import merge_graphs, pairing_identity


def pr(pid, work, period="2011", m="Q132952", f="Q32522", domain="on_screen"):
    return {"pairing_id": pid, "domain": domain, "period": period, "work": work,
            "male_qid": m, "female_qid": f, "male": "Adam Sandler",
            "female": "Jennifer Aniston"}


def test_the_same_film_from_two_graphs_collapses_to_one():
    imdb = [pr("pr_imdb_tt1564367_Q132952_Q32522", "Just Go with It")]
    wiki = [pr("pr_screen_Q747496_Q132952_Q32522", "Just Go with It")]
    kept, stats = merge_graphs([("imdb", imdb), ("wiki", wiki)])
    assert len(kept) == 1, "the same romance was counted twice"
    assert stats["duplicates_dropped"] == 1


def test_the_first_source_wins():
    """The IMDb record carries weight, confidence and characters; the Wikidata
    one does not. Passing IMDb first must keep the richer record."""
    imdb = [dict(pr("a", "Just Go with It"), weight="central")]
    wiki = [pr("b", "Just Go with It")]
    kept, _ = merge_graphs([("imdb", imdb), ("wiki", wiki)])
    assert kept[0]["weight"] == "central"


def test_title_spelling_differences_still_collapse():
    """Two sources punctuate differently. 'Mr. & Mrs. Smith' and
    'Mr & Mrs Smith' are one film."""
    a = [pr("a", "Mr. & Mrs. Smith")]
    b = [pr("b", "Mr & Mrs  Smith")]
    kept, _ = merge_graphs([("a", a), ("b", b)])
    assert len(kept) == 1


def test_two_different_films_in_one_year_both_survive():
    """A couple really can make two films in a year. Collapsing on the couple
    and the year alone would delete a real romance."""
    a = [pr("a", "Murder Mystery", period="2019"),
         pr("b", "Murder Mystery 2", period="2019")]
    kept, _ = merge_graphs([("a", a)])
    assert len(kept) == 2


def test_the_same_couple_in_different_years_both_survive():
    a = [pr("a", "Just Go with It", period="2011"),
         pr("b", "Murder Mystery", period="2019")]
    kept, _ = merge_graphs([("a", a)])
    assert len(kept) == 2


def test_on_screen_and_real_life_are_never_merged():
    """A couple who co-starred AND dated is two separate facts about them."""
    a = [pr("a", "Just Go with It", domain="on_screen"),
         pr("b", None, domain="real_life")]
    kept, _ = merge_graphs([("a", a)])
    assert len(kept) == 2


def test_a_real_life_pairing_with_no_work_still_dedupes():
    a = [pr("a", None, domain="real_life")]
    b = [pr("b", None, domain="real_life")]
    kept, stats = merge_graphs([("a", a), ("b", b)])
    assert len(kept) == 1 and stats["duplicates_dropped"] == 1


def test_a_pairing_missing_a_qid_is_reported_not_silently_merged():
    """Two pairings with no ids must not collapse into each other."""
    a = [pr("a", "X", m=None), pr("b", "Y", m=None)]
    kept, stats = merge_graphs([("a", a)])
    assert len(kept) == 2
    assert stats["without_both_qids"] == 2


def test_identity_is_order_independent_for_the_couple():
    """male_qid and female_qid are separate fields, so a graph that swapped
    them must still identify the same romance."""
    x = pairing_identity(pr("a", "Just Go with It"))
    y = pairing_identity(pr("b", "Just Go with It", m="Q32522", f="Q132952"))
    assert x == y


def test_stats_reconcile():
    a = [pr("a", "F1"), pr("b", "F2")]
    b = [pr("c", "F1"), pr("d", "F3")]
    kept, s = merge_graphs([("a", a), ("b", b)])
    assert s["seen"] == 4
    assert s["seen"] == len(kept) + s["duplicates_dropped"]


def test_per_source_counts_are_reported():
    kept, s = merge_graphs([("imdb", [pr("a", "F1")]), ("wiki", [pr("b", "F1")])])
    assert s["by_source"] == {"imdb": 1, "wiki": 0}


def test_an_alternate_cut_is_the_same_film():
    """IMDb gives a director's cut its own tconst, title AND year. Ben Affleck
    was credited with two romances with Jennifer Garner for one film."""
    a = [pr("a", "Daredevil", period="2003", f="Q172044"),
         pr("b", "Daredevil: The Director's Cut", period="2004", f="Q172044")]
    kept, stats = merge_graphs([("a", a)])
    assert len(kept) == 1, [c["work"] for c in kept]
    assert stats["duplicates_dropped"] == 1


def test_two_sources_disagreeing_about_the_year_still_collapse():
    """Release year against production year is the common case."""
    a = [pr("a", "Pearl Harbor", period="2001")]
    b = [pr("b", "Pearl Harbor", period="2000")]
    kept, _ = merge_graphs([("a", a), ("b", b)])
    assert len(kept) == 1


def test_a_sequel_is_not_an_alternate_cut():
    a = [pr("a", "Murder Mystery", period="2019"),
         pr("b", "Murder Mystery 2", period="2023")]
    assert len(merge_graphs([("a", a)])[0]) == 2


def test_a_film_whose_real_title_is_an_edition_word_keeps_its_name():
    """Stripping must never empty a title, or every such film collapses."""
    from modules.pairing.merge import normalise_work
    assert normalise_work("The Final Cut") != ""
    assert normalise_work("Unrated") != ""
    assert normalise_work("The Final Cut") != normalise_work("Unrated")


def test_real_life_keeps_the_period_so_a_rekindled_romance_survives():
    """Affleck and Lopez, 2004 and again 2022."""
    a = [pr("a", None, period="2004", domain="real_life", f="Q40715"),
         pr("b", None, period="2022", domain="real_life", f="Q40715")]
    assert len(merge_graphs([("a", a)])[0]) == 2
