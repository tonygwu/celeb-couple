"""The award-table parser, which produces 20 of the corpus's 41 observations.

It had no tests. Its documented behaviours — day/month/year precision from
`{{dts}}`, skipping rows it cannot date or link rather than guessing, and the
rowspan continuation rows that lose a handful of entries — were all asserted in
prose and by nothing else.

Precision matters most here. A year-precision award stored as a day would
manufacture a date no source asserted, which is the defect
`packages/temporal/dates.py` exists to prevent, and this parser is where those
dates enter.
"""
from __future__ import annotations

from packages.temporal.dates import Precision
from modules.consensus.wikipedia_lists import parse_award_table_with_stats


def _table(*rows: str) -> str:
    return "\n".join(rows)


def test_a_full_date_keeps_day_precision():
    rows, stats = parse_award_table_with_stats(
        "\n|-\n| {{dts|1985|11|4}}\n| [[Mel Gibson]]\n")
    assert len(rows) == 1
    assert rows[0].date_value == "1985-11-04" and rows[0].date_precision is Precision.DAY


def test_a_year_only_date_stays_a_year():
    """Storing it as 1985-01-01 would invent a day no source asserted."""
    rows, _ = parse_award_table_with_stats(
        "\n|-\n| {{dts|1985}}\n| [[Mel Gibson]]\n")
    assert rows[0].date_value == "1985" and rows[0].date_precision is Precision.YEAR


def test_a_year_and_month_stays_a_month():
    rows, _ = parse_award_table_with_stats(
        "\n|-\n| {{dts|1985|11}}\n| [[Mel Gibson]]\n")
    assert rows[0].date_value == "1985-11" and rows[0].date_precision is Precision.MONTH


def test_a_bare_four_digit_year_is_accepted():
    rows, _ = parse_award_table_with_stats("\n|-\n| 1990\n| [[Michelle Pfeiffer]]\n")
    assert rows[0].date_value == "1990" and rows[0].date_precision is Precision.YEAR


def test_a_row_with_no_date_is_skipped_and_counted():
    """A dateless row with no rowspan above it is still skipped.

    Rowspan continuation rows are now carried (see the tests below), so this
    covers what remains: a row whose date cell holds something the parser
    cannot read, with nothing declaring that it shares an earlier date.
    Guessing a year for it would invent a fact no source states."""
    _, stats = parse_award_table_with_stats(
        "\n|-\n| {{dts|1985|11|4}}\n| [[A]]\n"
        "\n|-\n| [[B]]\n| [[C]]\n")
    assert stats.skipped_no_date == 1
    assert stats.skipped == stats.skipped_no_date + stats.skipped_no_link


def test_a_row_whose_winner_cell_has_no_link_is_skipped_and_counted():
    """A plain-text cell is usually a note. Inventing a name from one is the
    quiet wrong answer this parser exists to avoid."""
    _, stats = parse_award_table_with_stats(
        "\n|-\n| {{dts|1985}}\n| no award this year\n")
    assert stats.skipped_no_link == 1


def test_a_piped_link_keeps_the_target_not_the_display_text():
    rows, _ = parse_award_table_with_stats(
        "\n|-\n| {{dts|1985}}\n| [[Mel Gibson|Gibson]]\n")
    assert rows[0].winner == "Mel Gibson"


def test_references_are_stripped_before_parsing():
    """A <ref> can contain a date, and parsing it would date the row from a
    citation rather than from the row."""
    rows, _ = parse_award_table_with_stats(
        "\n|-\n| {{dts|1985}}<ref>{{dts|1999}} retrieved</ref>\n| [[Mel Gibson]]\n")
    assert len(rows) == 1 and rows[0].date_value == "1985"


def test_every_block_is_counted_even_when_it_yields_nothing():
    """parsed + skipped can be less than row_blocks, and all three are
    recorded, so the discrepancy is visible rather than implied."""
    _, stats = parse_award_table_with_stats(
        "\n|-\n| {{dts|1985}}\n| [[A]]\n"
        "\n|-\n| single cell\n")
    assert stats.row_blocks >= stats.parsed + stats.skipped


def test_an_empty_table_parses_to_nothing_without_raising():
    rows, stats = parse_award_table_with_stats("")
    assert rows == [] and stats.parsed == 0


# ---------------------------------------------------------------------------
# rowspan continuation rows
#
# docs/BACKLOG.md called this one bug losing "3 in Sexiest Man Alive, 2 in Most
# Beautiful". It was two bugs. Only one of the three SMA rows was a rowspan
# continuation; the other two were the 2024 and 2025 winners, whose dates the
# table now writes in plain English. The second bug is the worse one, because
# it takes the NEWEST row every year and hides itself by shrinking the corpus
# rather than corrupting it.
# ---------------------------------------------------------------------------

def test_a_rowspan_date_carries_to_its_continuation_row():
    """People ran a 1993 "Sexiest Couple Alive": one date cell, two winners.

    The continuation row has no date cell, so every cell shifts left and the
    winner sits in cells[0]. Reading cells[1] there takes the age column.
    """
    rows, stats = parse_award_table_with_stats(
        '\n|-\n| rowspan="2" | {{dts|1993|10|19}}\n| [[Richard Gere]]\n| 44'
        "\n|-\n| [[Cindy Crawford]]\n| 27\n")
    assert [r.winner for r in rows] == ["Richard Gere", "Cindy Crawford"]
    assert {r.date_value for r in rows} == {"1993-10-19"}
    assert {r.date_precision for r in rows} == {Precision.DAY}
    assert stats.skipped_no_date == 0


def test_a_rowspan_of_three_carries_to_exactly_two_more():
    """People's 2020 Most Beautiful named three generations of one family."""
    rows, _ = parse_award_table_with_stats(
        '\n|-\n| rowspan="3" |{{dts|2020|5|4}}\n| [[Goldie Hawn]]\n| 74'
        "\n|-\n| [[Kate Hudson]] (2)\n| 41"
        "\n|-\n| [[Rani Fujikawa]]\n| 1\n")
    assert [r.winner for r in rows] == ["Goldie Hawn", "Kate Hudson", "Rani Fujikawa"]
    assert {r.date_value for r in rows} == {"2020-05-04"}


def test_the_carry_stops_at_the_declared_count():
    """A rowspan of 2 covers its own row and ONE more, never the row after.

    Carrying further would date a row from a table entry that never claimed
    it, which is the mis-dating the old skip existed to avoid.
    """
    rows, stats = parse_award_table_with_stats(
        '\n|-\n| rowspan="2" | {{dts|1993|10|19}}\n| [[A]]\n| 44'
        "\n|-\n| [[B]]\n| 27"
        "\n|-\n| [[C]]\n| 31\n")
    assert [r.winner for r in rows] == ["A", "B"]
    assert stats.skipped_no_date == 1, "the third row has no date and none was declared for it"


def test_a_new_date_cancels_an_unfinished_carry():
    """A malformed rowspan must not leak its date into a row that has one."""
    rows, _ = parse_award_table_with_stats(
        '\n|-\n| rowspan="3" | {{dts|1993|10|19}}\n| [[A]]\n| 44'
        "\n|-\n| {{dts|1994|10|18}}\n| [[B]]\n| 27\n")
    assert [(r.winner, r.date_value) for r in rows] == [
        ("A", "1993-10-19"), ("B", "1994-10-18")]


def test_a_row_with_no_rowspan_does_not_carry():
    """The default is still to skip. Carrying is opt-in, declared by the table."""
    _, stats = parse_award_table_with_stats(
        "\n|-\n| {{dts|1985|11|4}}\n| [[A]]\n| 30"
        "\n|-\n| [[B]]\n| 27\n")
    assert stats.skipped_no_date == 1


def test_an_unlinked_continuation_row_is_still_skipped_for_the_link():
    """People listed a one-year-old with no article. She gets a date and no link.

    The row moves from skipped_no_date to skipped_no_link, which is the honest
    reason: she is datable and simply is not a linked person.
    """
    rows, stats = parse_award_table_with_stats(
        '\n|-\n| rowspan="2" |{{dts|2020|5|4}}\n| [[Goldie Hawn]]\n| 74'
        "\n|-\n| Rani Hudson Fujikawa\n| 1\n")
    assert [r.winner for r in rows] == ["Goldie Hawn"]
    assert stats.skipped_no_date == 0 and stats.skipped_no_link == 1


# ---------------------------------------------------------------------------
# plain-English dates
# ---------------------------------------------------------------------------

def test_a_plain_english_date_is_read():
    """People wrote 2024 and 2025 as "November 13, 2024" instead of {{dts}}.

    Both winners were dropped silently. A parser that only knows one date
    format loses the newest row every year and reports it as a skip.
    """
    rows, stats = parse_award_table_with_stats(
        "\n|-\n|November 13, 2024\n|[[John Krasinski]]\n|45\n")
    assert rows[0].winner == "John Krasinski"
    assert rows[0].date_value == "2024-11-13"
    assert rows[0].date_precision is Precision.DAY
    assert stats.skipped_no_date == 0


def test_a_plain_english_date_survives_cell_attributes():
    rows, _ = parse_award_table_with_stats(
        '\n|-\n| style="text-align:center" | November 3, 2025\n|[[Jonathan Bailey]]\n|37\n')
    assert rows[0].date_value == "2025-11-03"


def test_an_unknown_month_name_is_skipped_not_guessed():
    """"Smarch" is not a month. A parser that reached for the nearest one, or
    defaulted to January, would invent a date no source asserts."""
    rows, stats = parse_award_table_with_stats(
        "\n|-\n|Smarch 13, 2024\n|[[John Krasinski]]\n|45\n")
    assert rows == [] and stats.skipped_no_date == 1


def test_a_day_out_of_a_plain_date_is_kept_verbatim():
    """Single-digit days must zero-pad rather than produce "2024-11-3"."""
    rows, _ = parse_award_table_with_stats(
        "\n|-\n|March 5, 2024\n|[[A]]\n")
    assert rows[0].date_value == "2024-03-05"
