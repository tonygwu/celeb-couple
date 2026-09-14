"""Parsing a table that carries ordered positions, not just a winner."""

from __future__ import annotations

from modules.consensus.ranked_lists import ORDINAL, parse_ranked_table

FHM_SHAPE = """
{|class="wikitable"
|-
!scope=row style="text-align:center;"|1995
|align=center|{{Sort|Schiffer, Claudia|[[File:Claudia.jpg|80px|alt=a photo]]<br />'''[[Claudia Schiffer]]'''}}
|
* <small>2nd: [[Uma Thurman]]</small>
* <small>5th: [[Michelle Pfeiffer]]</small>
|-
!scope=row style="text-align:center;"|1996
|align=center|{{Sort|Anderson, Gillian|[[File:Gillian.jpg|80px]]<br />'''[[Gillian Anderson]]'''}}
|
* <small>2nd: [[Louise Nurding]]</small>
|}
"""


def test_the_winner_is_the_person_not_the_photograph():
    """The winner cell's FIRST wiki-link is a [[File:]], not a human."""
    entries, _ = parse_ranked_table(FHM_SHAPE, list_length=100)
    winners = [e for e in entries if e.is_winner]
    assert [w.name for w in winners] == ["Claudia Schiffer", "Gillian Anderson"]
    assert not any(e.name.startswith(("File:", "Image:")) for e in entries)


def test_numbered_runner_up_positions_are_captured_with_their_ranks():
    entries, _ = parse_ranked_table(FHM_SHAPE, list_length=100)
    got = {(e.year, e.rank, e.name) for e in entries}
    assert (1995, 1, "Claudia Schiffer") in got
    assert (1995, 2, "Uma Thurman") in got
    assert (1995, 5, "Michelle Pfeiffer") in got
    assert (1996, 2, "Louise Nurding") in got


def test_rank_is_recorded_against_the_sources_list_length_not_the_rows_shown():
    """5th of 100 is a far weaker placement than 5th of 10. The table shows ten
    positions; the source publishes a hundred."""
    entries, _ = parse_ranked_table(FHM_SHAPE, list_length=100)
    pfeiffer = next(e for e in entries if e.name == "Michelle Pfeiffer")
    assert pfeiffer.rank == 5
    # list_length travels with the record, not with the parse
    from modules.consensus.ranked_lists import ranked_to_records
    _, obs = ranked_to_records(
        [pfeiffer], page="P", section_title="S", publisher="Pub", list_title="L",
        list_length=100, order_basis="the table numbers each position",
        candidate_pool="women in entertainment", source_url="https://example.invalid",
        content_hash="0" * 64, retrieved_at_utc="2026-09-14T00:00:00Z",
        name_to_person={"Michelle Pfeiffer": "Q1"},
    )
    assert obs[0].observed["list_length"] == 100
    assert obs[0].observed["rank"] == 5


def test_a_rank_beyond_the_list_length_is_dropped():
    text = FHM_SHAPE.replace("5th: [[Michelle Pfeiffer]]", "500th: [[Michelle Pfeiffer]]")
    entries, _ = parse_ranked_table(text, list_length=100)
    assert not any(e.name == "Michelle Pfeiffer" for e in entries)


def test_a_duplicate_rank_in_one_year_is_not_double_counted():
    text = FHM_SHAPE.replace(
        "* <small>2nd: [[Uma Thurman]]</small>",
        "* <small>2nd: [[Uma Thurman]]</small>\n* <small>2nd: [[Uma Thurman]]</small>",
    )
    entries, _ = parse_ranked_table(text, list_length=100)
    assert sum(1 for e in entries if e.name == "Uma Thurman") == 1


def test_ranked_observations_carry_the_order_basis_that_justifies_the_rank():
    from modules.consensus.ranked_lists import RankedEntry, ranked_to_records
    _, obs = ranked_to_records(
        [RankedEntry(2001, 3, "Ada Vance", False)], page="P", section_title="S",
        publisher="Pub", list_title="L", list_length=100,
        order_basis="the table numbers each position explicitly",
        candidate_pool="women in entertainment", source_url="https://example.invalid",
        content_hash="0" * 64, retrieved_at_utc="2026-09-14T00:00:00Z",
        name_to_person={"Ada Vance": "Q1"},
    )
    assert obs[0].observed["order_is_ranking"] is True
    assert "numbers each position" in obs[0].observed["order_basis"]


def test_the_ordinal_pattern_does_not_match_a_file_link():
    assert ORDINAL.findall("3rd: [[File:x.jpg|thumb]]") == []
    assert ORDINAL.findall("3rd: [[Ada Vance]]") == [("3", "Ada Vance")]
