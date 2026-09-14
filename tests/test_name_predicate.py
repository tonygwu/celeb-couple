"""What may be read as a person's name out of a plain table cell.

Both parsers in modules/consensus face this, and the predicate was written
twice within an hour of consolidating the User-Agent for exactly that reason.
It lives in one module now, and these tests pin the boundary in both
directions, because the cost of the two mistakes is not symmetric: a refused
cell is counted and stays visible, while an accepted one puts a person into the
corpus who may not exist.
"""
from __future__ import annotations

import pytest

from modules.consensus.names import looks_like_a_name


@pytest.mark.parametrize("text", [
    "Eva Longoria",                # Maxim 2006, the row that started this
    "Rani Hudson Fujikawa",        # People's Most Beautiful 2020
    "Rosie Jones",                 # FHM 2012, rank 4
    "Catherine Zeta-Jones",        # hyphen
    "Sinead O'Connor",             # apostrophe
    "Sinead O’Connor",        # typographic apostrophe
    "Michael J. Fox",              # initial
    "  Eva Longoria  ",            # surrounding whitespace
])
def test_these_read_as_names(text):
    assert looks_like_a_name(text)


@pytest.mark.parametrize("text", [
    "First and only woman to win twice in a row.",  # the real Maxim note
    "not awarded",
    "not awarded that year",
    "Unknown",                     # single word: commoner as a placeholder
    "None",
    "Vacant",
    "",
    "   ",
    "1998",
    "see below",
    "TBA",
])
def test_these_do_not(text):
    assert not looks_like_a_name(text)


def test_a_six_word_cell_is_refused():
    """Five words is already generous for a name; beyond that it is prose."""
    assert not looks_like_a_name("One Two Three Four Five Six")


def test_the_predicate_alone_puts_nobody_in_the_corpus():
    """It is a filter in front of a roster lookup, not a decision.

    Both callers then look the name up in name_to_person and emit an
    observation only for somebody the roster already names. This test exists so
    that the docstring's claim is checked against the callers rather than
    trusted.
    """
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    for rel in ("modules/consensus/wikipedia_lists.py",
                "modules/consensus/ranked_lists.py"):
        body = (repo / rel).read_text()
        assert "looks_like_a_name" in body, rel
        assert "name_to_person" in body, (
            f"{rel} accepts unlinked names without a roster lookup behind it")


def test_only_one_module_defines_the_pattern():
    """It was duplicated once already. The copy that drifts is the unread one."""
    import re
    from pathlib import Path
    repo = Path(__file__).resolve().parent.parent
    definers = [p.relative_to(repo)
                for base in ("modules", "scripts", "packages")
                for p in sorted((repo / base).rglob("*.py"))
                if re.search(r"^NAME_PATTERN\s*=|^_LOOKS_LIKE_A_NAME\s*=",
                             p.read_text(), re.M)]
    assert definers == [Path("modules/consensus/names.py")], definers
