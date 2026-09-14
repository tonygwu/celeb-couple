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
    """The commonest case is a rowspan continuation row: when one year names
    several people, only the first carries the date cell. Losing them is safe;
    MIS-DATING them would not be, and the count makes the loss visible."""
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
