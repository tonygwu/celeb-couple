"""IMDb ids join to Wikidata by P345, never by name.

The score cache and the published observations key on a Wikidata QID. The IMDb
graph keys on an nconst. Joining them on names would merge two people who share
one, and this corpus already contains such collisions -- resolve_imdb_people.py
found four Wikidata items answering to "Julia Roberts" and three to "Robert
Redford" when the seed roster was resolved.
"""
from __future__ import annotations

import re
from pathlib import Path

from scripts.resolve_imdb_people import ROW_LIMIT, build

REPO = Path(__file__).resolve().parent.parent


def test_the_query_joins_on_p345_and_not_on_a_label():
    q = build(["nm0000138"])
    assert "wdt:P345" in q
    assert "rdfs:label" not in q, "a label join would merge distinct people"


def test_the_query_restricts_to_humans():
    """P345 is also carried by films and companies."""
    assert "wdt:P31 wd:Q5" in build(["nm0000138"])


def test_every_item_in_the_chunk_reaches_the_query():
    chunk = [f"nm{i:07d}" for i in range(50)]
    q = build(chunk)
    for n in chunk:
        assert f'"{n}"' in q


def test_the_row_cap_is_far_above_any_honest_answer():
    """A cap a real answer can reach is silent data loss. One query capped at
    400 against 2,570 rows published 136 pairs instead of 808."""
    assert ROW_LIMIT >= 5000
    assert f"LIMIT {ROW_LIMIT}" in build(["nm0000138"])


def test_the_query_is_distinct():
    """A person whose P31 reaches Q5 by several paths yields one row per path,
    and those duplicates count against the cap."""
    assert re.search(r"SELECT\s+DISTINCT", build(["nm0000138"]))


def test_it_uses_the_guarded_batcher_not_a_bare_query_loop():
    src = (REPO / "scripts/resolve_imdb_people.py").read_text()
    assert "batched_query" in src
    # `batched_query(` contains the substring `_query(`, so match a call that
    # is NOT the tail of a longer identifier.
    bare = re.search(r"(?<![A-Za-z0-9_])_query\s*\(", src)
    assert bare is None, (
        "a bare _query loop skips the at-the-cap and timeout guards")
