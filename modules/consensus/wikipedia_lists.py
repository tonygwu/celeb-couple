"""Extract dated award facts from Wikipedia's own tables.

WHY THIS ROUTE
--------------
That a given person was named "Sexiest Man Alive" in a given year is a FACT.
Wikipedia states it under CC BY-SA with a citation back to the publisher, and
reading Wikipedia is not reading the publisher's site.

This matters because the publishers that hold most of this evidence forbid the
operation outright.  people.com's robots.txt prohibits "development or
operation of any artificial intelligence, machine learning, or large language
model (LLM) technology, including ... retrieval-augmented generation" and
"creating data sets containing People Inc. content".  askmen.com (Ziff Davis)
carries the same wording.  maxim.com blocks ClaudeBot, GPTBot and CCBot.
So this module reads Wikipedia and nothing else.

What it produces is an EDITORIAL_AWARD observation per winner-year.  It does
not produce a rank, because a one-winner award is not a ranking of anybody
else, and it does not produce anything at all for a person who is absent.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

from packages.ids.keys import content_sha256, stable_id
from packages.schema.records import EvidenceType, Lineage, ListEdition, Observation
from packages.temporal.dates import Precision, PreciseDate

__all__ = ["AwardRow", "TableStats", "fetch_section_wikitext", "parse_award_table",
           "parse_award_table_with_stats", "to_records"]

API = "https://en.wikipedia.org/w/api.php"
#: Imported, not copied. See packages/wiki/fetch.py.
from packages.wiki.fetch import USER_AGENT  # noqa: E402,F401

#: {{dts|1985|2|4}} -> 1985-02-04 ; {{dts|1985}} -> 1985
_DTS = re.compile(r"\{\{dts\|(\d{4})(?:\|(\d{1,2}))?(?:\|(\d{1,2}))?[^}]*\}\}")
_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
_REF = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.S)
#: ``rowspan="3"`` on a date cell: the table itself declaring how many rows
#: share that date. Read, never guessed.
_ROWSPAN = re.compile(r'rowspan\s*=\s*"?(\d+)"?', re.I)
#: Shared with the sibling parser. See modules/consensus/names.py.
from modules.consensus.names import looks_like_a_name
#: "November 13, 2024" -- People switched the Sexiest Man Alive table to plain
#: English dates in 2024, and the {{dts}}-only parser dropped every row that
#: used them.
_PLAIN_DATE = re.compile(
    r"^\s*([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})\s*$")
_MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], start=1)}


@dataclass(frozen=True)
class TableStats:
    """How much of the table was read, so coverage has a visible denominator."""

    row_blocks: int
    parsed: int
    skipped_no_date: int
    skipped_no_link: int
    #: Winners the source named in plain text rather than a wiki-link, now
    #: parsed instead of dropped. Reported separately so a reader can see how
    #: many rows rest on a name that carried no link.
    unlinked_recovered: int = 0

    @property
    def skipped(self) -> int:
        return self.skipped_no_date + self.skipped_no_link


@dataclass(frozen=True)
class AwardRow:
    year: int
    date_value: str
    date_precision: Precision
    winner: str
    raw_cell: str
    #: False when the source named the winner in plain text rather than a
    #: wiki-link. Such a row only becomes an observation if the name matches a
    #: roster member exactly, so it invents nobody.
    linked: bool = True


def fetch_section_wikitext(page: str, section: int) -> tuple[str, str]:
    """Return (wikitext, sha256 of the exact bytes retrieved)."""
    url = API + "?" + urllib.parse.urlencode({
        "action": "parse", "page": page, "prop": "wikitext",
        "section": str(section), "format": "json", "formatversion": "2",
    })
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as fh:
        raw = fh.read()
    return json.loads(raw)["parse"]["wikitext"], content_sha256(raw)


def parse_award_table(wikitext: str) -> list[AwardRow]:
    return parse_award_table_with_stats(wikitext)[0]


def parse_award_table_with_stats(wikitext: str) -> tuple[list[AwardRow], TableStats]:
    """Parse a two-or-three-column wikitable of date + winner.

    Rows whose winner cell holds no wiki-link, or whose date cell holds no
    date, are SKIPPED rather than guessed at. A plain-text cell is usually a
    note, and inventing a name or a year from one is exactly the kind of quiet
    wrong answer this project exists to avoid.

    The commonest skip is a ``rowspan`` continuation row: when one year names
    several people, only the first carries the date cell and the rest look
    dateless. Measured on People's Most Beautiful table, that loses the two
    continuation rows of the 2020 entry. Losing them is safe; MIS-DATING them
    would not be. The count is returned so the loss is visible.
    """
    rows: list[AwardRow] = []
    no_date = no_link = 0
    unlinked_recovered = 0
    carried = 0          # rows still covered by the last rowspan
    carry: tuple[str, Precision, str] | None = None
    body = _REF.sub("", wikitext)
    blocks = body.split("\n|-")
    for block in blocks:
        cells = [c.strip() for c in block.split("\n|")[1:]]
        if len(cells) < 2:
            continue
        parsed = _parse_date_cell(cells[0])
        if parsed:
            value, prec, y = parsed
            # The date cell says how many rows it covers. Its own row is one
            # of them, so N=3 carries to the next two.
            span = _ROWSPAN.search(cells[0])
            carried = int(span.group(1)) - 1 if span else 0
            carry = (value, prec, y) if carried > 0 else None
            winner_cell = cells[1]
        elif carried > 0 and carry is not None:
            # A continuation row has no date cell at all, so every cell shifts
            # left: the winner is cells[0], not cells[1]. Reading cells[1]
            # here would take the age column and find no link in it.
            value, prec, y = carry
            carried -= 1
            winner_cell = cells[0]
        else:
            no_date += 1
            carry, carried = None, 0
            continue
        link = _LINK.search(winner_cell)
        if not link:
            # Maxim names its 2006 winner, Eva Longoria, in plain text. The
            # row was counted as a no-link skip and dropped, which is right
            # for a note and wrong for a name. Emitting it costs nothing:
            # `to_records` only produces an observation for a winner already
            # in `name_to_person`.
            bare = _strip_markup(winner_cell)
            if looks_like_a_name(bare):
                rows.append(AwardRow(int(y), value, prec, bare,
                                     winner_cell[:120], linked=False))
                unlinked_recovered += 1
                continue
            no_link += 1
            continue
        rows.append(AwardRow(int(y), value, prec, link.group(1).strip(),
                             winner_cell[:120]))
    return rows, TableStats(
        row_blocks=max(0, len(blocks) - 1), parsed=len(rows),
        skipped_no_date=no_date, skipped_no_link=no_link,
        unlinked_recovered=unlinked_recovered,
    )


def _strip_markup(cell: str) -> str:
    """The plain text of a table cell, or "" if anything but text is left.

    Cell attributes, a trailing "(2)" repeat marker and an &nbsp; are removed
    because they are formatting. Anything still carrying markup returns empty
    and the row stays a counted skip.
    """
    text = cell.split("|")[-1] if "|" in cell else cell
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"\s*\(\d+\)\s*$", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    return "" if ("[" in text or "{" in text) else text.strip()


def _parse_date_cell(cell: str) -> tuple[str, Precision, str] | None:
    """Read a date cell in any of the three shapes these tables use.

    Returns None when the cell holds no date, which is how a continuation row
    is recognised. A cell that holds SOMETHING unparseable also returns None
    and is counted as a skip rather than guessed at.
    """
    m = _DTS.search(cell)
    if m:
        y, mo, d = m.group(1), m.group(2), m.group(3)
        if mo and d:
            return f"{int(y):04d}-{int(mo):02d}-{int(d):02d}", Precision.DAY, y
        if mo:
            return f"{int(y):04d}-{int(mo):02d}", Precision.MONTH, y
        return y, Precision.YEAR, y
    # Strip any cell attributes ("rowspan=2 | November 13, 2024") before
    # matching the text.
    text = cell.split("|")[-1].strip() if "|" in cell else cell.strip()
    plain = _PLAIN_DATE.match(text)
    if plain and plain.group(1) in _MONTHS:
        y, mo, d = plain.group(3), _MONTHS[plain.group(1)], int(plain.group(2))
        return f"{int(y):04d}-{mo:02d}-{d:02d}", Precision.DAY, y
    bare = re.match(r"^\s*(\d{4})\s*$", text)
    if bare:
        return bare.group(1), Precision.YEAR, bare.group(1)
    return None


def to_records(
    rows: list[AwardRow],
    *,
    page: str,
    section_title: str,
    publisher: str,
    award_name: str,
    candidate_pool: str,
    source_url: str,
    content_hash: str,
    retrieved_at_utc: str,
    name_to_person: dict[str, str],
) -> tuple[list[ListEdition], list[Observation]]:
    """One ListEdition per year, one EDITORIAL_AWARD observation per winner.

    Only winners who are in ``name_to_person`` produce an observation. Everyone
    else on the list is simply not this pilot's subject; their absence from the
    output is not evidence about them.
    """
    editions: list[ListEdition] = []
    observations: list[Observation] = []
    for row in rows:
        pid = name_to_person.get(row.winner)
        edition_id = stable_id("le", page, section_title, str(row.year))
        published = PreciseDate(row.date_value, row.date_precision, edition_id)
        concerns = PreciseDate(str(row.year), Precision.YEAR, edition_id)
        edition = ListEdition(
            list_edition_id=edition_id, publisher=publisher,
            title=f"{award_name} {row.year}", source_url=source_url,
            published_at=published, concerns_period=concerns,
            access_route="wikipedia-api",
            retrieved_at_utc=retrieved_at_utc, content_sha256=content_hash,
            candidate_set_described=candidate_pool,
            list_length=1,
            licence="CC BY-SA 4.0 (Wikipedia); the underlying selection is the publisher's",
            attribution=f"Fact reported by English Wikipedia, '{page}', section '{section_title}'",
        )
        editions.append(edition)
        if pid is None:
            continue
        observations.append(Observation(
            observation_id=stable_id("obs", edition_id, pid),
            person_id=pid, list_edition_id=edition_id,
            evidence_type=EvidenceType.EDITORIAL_AWARD,
            observed={"award_name": award_name, "winner": True},
            concerns_period=concerns, published_at=published,
            lineage=Lineage(original_source=edition_id),
            excerpt=f"{row.winner} — {award_name} {row.year}",
            excerpt_locator=f"{section_title} table, row for {row.date_value}",
            review_status="pending",
        ))
    return editions, observations
