"""Parse a Wikipedia table that carries ORDERED positions, not just a winner.

WHY THIS EXISTS
---------------
M0 measured the problem this module solves. Every estimate it produced landed
between 92.0 and 92.5, because every observation was a one-winner annual award
and a one-winner award is superlative by construction. Award-shaped evidence
cannot tell winners apart, so a board built on it ranks people by the gap
between one judge saying 92 and another saying 93.

Ranked evidence has the shape that can discriminate: 5th of 100 is a different
judgment from 1st of 100, and the rubric can say so.

THE TABLE SHAPE
---------------
FHM's list uses a header cell for the year, a ``{{Sort|...}}`` template holding
the winner, and a bulleted runner-up column::

    |-
    !scope=row style="text-align:center;"|1995
    |align=center|{{Sort|Schiffer, Claudia|[[File:...]]<br />'''[[Claudia Schiffer]]'''}}
    |
    * <small>2nd: [[Uma Thurman]]</small>
    * <small>3rd: [[Nastassja Kinski]]</small>

The winner cell also contains a ``[[File:...]]`` link, so the FIRST wiki-link in
that cell is an image, not a person. Taking it would file every year's winner
under a photograph. The person is the link inside the bold markup.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["RankedEntry", "parse_ranked_table", "ORDINAL"]

#: "!scope=row ...|1995" or "! 1995"
_YEAR_HEADER = re.compile(r"^!.*?\|\s*(\d{4})\s*$|^!\s*(\d{4})\s*$", re.M)
#: the winner, inside bold markup, skipping any [[File:...]] that precedes it
_BOLD_LINK = re.compile(r"'''\[\[([^\]|]+?)(?:\|[^\]]*)?\]\]'''")
_ANY_LINK = re.compile(r"\[\[(?!File:|Image:)([^\]|]+?)(?:\|[^\]]*)?\]\]")
#: "* <small>2nd: [[Uma Thurman]]</small>"
ORDINAL = re.compile(
    r"(\d{1,3})(?:st|nd|rd|th)\s*:\s*\[\[(?!File:|Image:)([^\]|]+?)(?:\|[^\]]*)?\]\]"
)
#: The same position written WITHOUT a wiki-link: "* <small>4th: Rosie Jones".
#: FHM's 2012 list does this for rank 4, and the position was dropped in
#: silence -- the year simply came out with nine entries instead of ten and no
#: statistic said so.
ORDINAL_UNLINKED = re.compile(
    r"(\d{1,3})(?:st|nd|rd|th)\s*:\s*([^\[\]<>*|\n]+?)\s*(?:</small>|\n|$)"
)
#: What an unlinked cell has to look like before it is read as a person's name.
#: Deliberately strict. A plain-text cell is usually a note, and the cost of
#: being wrong is a fabricated person in the corpus; the cost of being too
#: strict is a position that stays dropped and COUNTED, which is what the
#: statistics are for.
_LOOKS_LIKE_A_NAME = re.compile(r"^[A-Z][A-Za-z.'\u2019\-]*(?: [A-Z][A-Za-z.'\u2019\-]*){1,4}$")
_REF = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.S)


@dataclass(frozen=True)
class RankedEntry:
    year: int
    rank: int
    name: str
    is_winner: bool
    #: False when the source named the person in plain text rather than a
    #: wiki-link. Such an entry only ever becomes an observation if the name
    #: matches a roster member exactly, so it invents nobody -- but a reader
    #: should be able to tell the two apart.
    linked: bool = True


def parse_ranked_table(
    wikitext: str, *, list_length: int
) -> tuple[list[RankedEntry], dict[str, int]]:
    """Return (entries, stats).

    ``list_length`` is the length the SOURCE says the list is (FHM publishes
    100), not the number of places the table happens to reproduce. A rank of 5
    means fifth of a hundred, and recording it as fifth of ten would overstate
    the placement badly.
    """
    body = _REF.sub("", wikitext)
    entries: list[RankedEntry] = []
    stats = {"blocks": 0, "years_found": 0, "no_year": 0, "no_winner": 0,
             "runner_up_positions": 0,
             # How often each heuristic was actually load-bearing. Without
             # these, a run whose every winner came from the ambiguous
             # fallback looked identical to one where every winner was bold.
             "winner_from_fallback": 0,
             "rank_beyond_declared_length": 0,
             # An unlinked position used to vanish without trace. Both halves
             # are counted: the ones recovered, and the ones whose cell did
             # not look like a name and stay dropped.
             "unlinked_positions_recovered": 0,
             "unlinked_positions_rejected": 0}

    for block in body.split("\n|-"):
        stats["blocks"] += 1
        m = _YEAR_HEADER.search(block)
        if not m:
            stats["no_year"] += 1
            continue
        year = int(m.group(1) or m.group(2))
        stats["years_found"] += 1

        winner = _BOLD_LINK.search(block)
        if winner:
            entries.append(RankedEntry(year, 1, winner.group(1).strip(), True))
        else:
            # Fall back to the first non-File link, which is where a table
            # without bold markup keeps the winner. Never take a File link:
            # that would file the year's winner under a photograph.
            alt = _ANY_LINK.search(block)
            if alt:
                entries.append(RankedEntry(year, 1, alt.group(1).strip(), True))
                stats["winner_from_fallback"] += 1
            else:
                stats["no_winner"] += 1

        seen_ranks = {1}
        for rank_s, name in ORDINAL.findall(block):
            rank = int(rank_s)
            if rank > list_length:
                # Correct to skip -- the source says how long its list is --
                # but skipping silently made a table that disagrees with its
                # declared length look like one that simply stopped early.
                stats["rank_beyond_declared_length"] += 1
                continue
            if rank in seen_ranks:
                continue
            seen_ranks.add(rank)
            entries.append(RankedEntry(year, rank, name.strip(), False))
            stats["runner_up_positions"] += 1

        # Second pass for positions the source wrote without a link. Ranks
        # already filled by a linked entry are left alone, so a link always
        # wins over plain text for the same position.
        for rank_s, raw in ORDINAL_UNLINKED.findall(block):
            rank = int(rank_s)
            if rank > list_length or rank in seen_ranks:
                continue
            candidate = raw.strip()
            if not _LOOKS_LIKE_A_NAME.match(candidate):
                stats["unlinked_positions_rejected"] += 1
                continue
            seen_ranks.add(rank)
            entries.append(RankedEntry(year, rank, candidate, False, linked=False))
            stats["unlinked_positions_recovered"] += 1
            stats["runner_up_positions"] += 1

    return entries, stats


def ranked_to_records(
    entries: list["RankedEntry"],
    *,
    page: str,
    section_title: str,
    publisher: str,
    list_title: str,
    list_length: int,
    order_basis: str,
    candidate_pool: str,
    source_url: str,
    content_hash: str,
    retrieved_at_utc: str,
    name_to_person: dict[str, str],
):
    """Turn ranked entries into ListEditions and ORDERED_RANK Observations.

    Only cohort members produce an observation. Everyone else on the list is
    simply not this project's subject, and their absence from the output says
    nothing about them.
    """
    from packages.ids.keys import stable_id
    from packages.schema.records import (
        EvidenceType, Lineage, ListEdition, Observation,
    )
    from packages.temporal.dates import Precision, PreciseDate

    editions: dict[str, ListEdition] = {}
    observations: list = []
    for e in entries:
        pid = name_to_person.get(e.name)
        edition_id = stable_id("le", page, section_title, str(e.year))
        if edition_id not in editions:
            when = PreciseDate(str(e.year), Precision.YEAR, edition_id)
            editions[edition_id] = ListEdition(
                list_edition_id=edition_id, publisher=publisher,
                title=f"{list_title} {e.year}", source_url=source_url,
                published_at=when, concerns_period=when,
                access_route="wikipedia-api", retrieved_at_utc=retrieved_at_utc,
                content_sha256=content_hash, candidate_set_described=candidate_pool,
                list_length=list_length,
                licence="CC BY-SA 4.0 (Wikipedia); the ranking itself is the publisher's",
                attribution=f"Fact reported by English Wikipedia, '{page}', section '{section_title}'",
            )
        if pid is None:
            continue
        when = editions[edition_id].concerns_period
        observations.append(Observation(
            observation_id=stable_id("obs", edition_id, pid, str(e.rank)),
            person_id=pid, list_edition_id=edition_id,
            evidence_type=EvidenceType.ORDERED_RANK,
            observed={
                "rank": e.rank, "list_length": list_length,
                "order_is_ranking": True, "order_basis": order_basis,
            },
            concerns_period=when, published_at=when,
            lineage=Lineage(original_source=edition_id),
            excerpt=f"{e.rank}. {e.name} — {list_title} {e.year}",
            excerpt_locator=f"{section_title} table, {e.year} row, position {e.rank}",
            review_status="pending",
        ))
    return list(editions.values()), observations
