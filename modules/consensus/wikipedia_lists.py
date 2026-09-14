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

__all__ = ["AwardRow", "fetch_section_wikitext", "parse_award_table", "to_records"]

API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = (
    "celeb-couple-M0/0.1 (https://github.com/tonygwu/celeb-couple; read-only research)"
)

#: {{dts|1985|2|4}} -> 1985-02-04 ; {{dts|1985}} -> 1985
_DTS = re.compile(r"\{\{dts\|(\d{4})(?:\|(\d{1,2}))?(?:\|(\d{1,2}))?[^}]*\}\}")
_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
_REF = re.compile(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>", re.S)


@dataclass(frozen=True)
class AwardRow:
    year: int
    date_value: str
    date_precision: Precision
    winner: str
    raw_cell: str


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
    """Parse a two-or-three-column wikitable of date + winner.

    Rows whose winner cell holds no wiki-link are skipped rather than guessed
    at: a plain-text cell is usually a note, and inventing a name from one is
    exactly the kind of quiet wrong answer this project is built to avoid.
    """
    rows: list[AwardRow] = []
    body = _REF.sub("", wikitext)
    for block in body.split("\n|-"):
        cells = [c.strip() for c in block.split("\n|")[1:]]
        if len(cells) < 2:
            continue
        m = _DTS.search(cells[0])
        if m:
            y, mo, d = m.group(1), m.group(2), m.group(3)
            if mo and d:
                value, prec = f"{int(y):04d}-{int(mo):02d}-{int(d):02d}", Precision.DAY
            elif mo:
                value, prec = f"{int(y):04d}-{int(mo):02d}", Precision.MONTH
            else:
                value, prec = y, Precision.YEAR
        else:
            bare = re.match(r"^\s*(\d{4})\s*$", cells[0])
            if not bare:
                continue
            value, prec, y = bare.group(1), Precision.YEAR, bare.group(1)
        link = _LINK.search(cells[1])
        if not link:
            continue
        rows.append(AwardRow(int(y), value, prec, link.group(1).strip(), cells[1][:120]))
    return rows


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
