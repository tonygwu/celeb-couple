"""The source verifier has to be able to FAIL.

Nothing in this project checked the observations against the pages they were
extracted from until `scripts/verify_observations.py` existed. It currently
reports 41 of 41, which is the reading a completely broken checker also
produces. So every rule here is tested in both directions against fixture
wikitext, and the fixture is a trimmed copy of the real FHM table rather than
an idealised one.

No test in this file touches the network. The script's own network calls are
not exercised; its parsing rules are.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

#: Trimmed from the live "FHM's 100 Sexiest Women (UK)" section 2. The image
#: link before the bolded name is the trap: it contains the same person's name
#: and must not be read as the answer.
BLOCK_2000 = (
    '\n!scope=row style="text-align:center;"|2000\n'
    '|align=center|{{Sort|Lopez, Jennifer|'
    '[[File:Jennifer Lopez 2, 2012.jpg|80px|alt=Colour photograph]]<br />'
    "'''[[Jennifer Lopez]]'''}}\n|\n"
    "* <small>2nd: [[Britney Spears]]</small>\n"
    "* <small>3rd: [[Sarah Michelle Gellar]]</small>\n"
    "* <small>4th: [[Anna Kournikova]]</small>\n"
)


def _mod():
    spec = importlib.util.spec_from_file_location(
        "verify_observations", REPO / "scripts/verify_observations.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def test_finds_the_number_one_and_not_the_image_caption():
    """The bold marks the winner. The image link names her too, earlier."""
    assert _mod().name_at(BLOCK_2000, 1) == "Jennifer Lopez"


def test_finds_a_ranked_entry():
    m = _mod()
    assert m.name_at(BLOCK_2000, 2) == "Britney Spears"
    assert m.name_at(BLOCK_2000, 4) == "Anna Kournikova"


def test_returns_none_for_a_rank_the_block_does_not_carry():
    """Absence must read as absence, never as the nearest available name."""
    assert _mod().name_at(BLOCK_2000, 9) is None


def test_an_unbolded_block_yields_no_winner():
    """If the table stops bolding the winner, say nothing rather than guess."""
    assert _mod().name_at(BLOCK_2000.replace("'''", ""), 1) is None


def test_rank_two_does_not_match_rank_twelve():
    """A bare \\b2nd\\b search would hit '12nd', and \\b2 would hit '2000'."""
    block = "* <small>12th: [[Someone Else]]</small>\n"
    assert _mod().name_at(block, 2) is None


@pytest.mark.parametrize("n,suffix", [
    (1, "st"), (2, "nd"), (3, "rd"), (4, "th"),
    (11, "th"), (12, "th"), (13, "th"),
    (21, "st"), (22, "nd"), (23, "rd"), (24, "th"),
    (101, "st"), (111, "th"), (112, "th"), (113, "th"),
])
def test_ordinal_suffix(n, suffix):
    """The original table returned 'th' for 21, so it searched for '21th'."""
    assert _mod().ordinal_suffix(n) == suffix


def test_norm_collapses_whitespace_without_joining_words():
    m = _mod()
    assert m._norm("  a \n b\tc  ") == "a b c"
    assert m._norm("ranked at\nnumber 79") == "ranked at number 79"


def test_every_publisher_in_the_corpus_has_a_table_location():
    """A publisher missing from TABLES is reported unverifiable, not verified.

    This asserts the corpus is fully covered today. If it starts failing, the
    fix is to add the location, not to relax the check: an observation nobody
    can verify should not be silently counted as one that passed.
    """
    import json
    m = _mod()
    path = REPO / "data/pilot/observations/observations.json"
    if not path.exists():
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")
    obs = json.loads(path.read_text())
    editions = {e["list_edition_id"]: e for e in obs["editions"]}
    missing = sorted({
        editions[o["list_edition_id"]].get("publisher", "")
        for o in obs["observations"]
        if o["excerpt_locator"] != "biographical article prose"
    } - set(m.TABLES))
    assert missing == [], f"no table location recorded for {missing}"


def test_the_recorded_result_is_a_full_pass():
    """Guards the claim the report makes: EVERY observation was confirmed.

    The claim is "verified == checked", not "verified == 41". This asserted the
    literal 41 and failed when the corpus legitimately grew to 42 on a full
    pass -- a hand-typed number going stale and then lying, which is the exact
    defect `scripts/audit_doc_numbers.py` exists to catch in prose. A test is
    not exempt from it.

    The COUNT is still checked, by the doc audit, against whatever the artifact
    says. Here the invariant is the shape of the result.
    """
    import json
    path = REPO / "data/pilot/run/observation_verification.json"
    if not path.exists():
        pytest.skip("data/ is gitignored; run scripts/verify_observations.py")
    payload = json.loads(path.read_text())
    assert payload["not_verified"] == []
    assert payload["unverifiable"] == []
    assert payload["verified"] == payload["checked"]
    # Guards against a vacuous pass: 0 == 0 is also "every observation
    # verified", and would satisfy every assertion above.
    assert payload["checked"] > 0, "nothing was checked; this proves nothing"
