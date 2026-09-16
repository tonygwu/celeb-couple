"""No age term exists anywhere in the pairing scoring path.

Plan v4 §2 reverses the "visual scoring" half of a constraint the operator set,
and explicitly keeps the rest. One of the parts kept is v3's ban on an
"automatic age-decline formula".

A pairing is judged at its own date, and if an estimate falls as someone ages
that is the judge's per-pairing assessment. It must never be a curve applied by
code, because a curve would manufacture the project's headline result -- the
late-career pairings that generate the largest gaps -- out of arithmetic rather
than judgment.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

#: Everything that can touch a pairing score. `score_pairings.py` and the
#: `rubrics/pairing/` files are SUPERSEDED (AGENTS.md, plan v4 §4a) and stay
#: here because superseded is not deleted and the guarantee is about the whole
#: scoring surface, not only the live half.
_SCORING_PATH = (
    "scripts/score_pairings.py",
    "scripts/select_m1_slice.py",
    "modules/pairing/judge.py",
    "rubrics/pairing/PAIRING.md",
    "rubrics/pairing/pairing.schema.json",
)

#: The CURRENT person-year scorer. Everything real has been graded through this
#: since 2026-09-15, and until now no test in this file named any of it, so the
#: project's strongest public claim -- that no image ever reaches a judge -- was
#: pinned only on the path that stopped being used.
_PERSON_SCORING_PATH = (
    "scripts/score_person_periods.py",
    "modules/pairing/person.py",
    "rubrics/person/person.schema.json",
)

#: Rubric PROSE is checked differently from code. `rubrics/person/PERSON.md`
#: tells the judge to weigh "their photographs, appearances, magazine coverage",
#: meaning what the model already knows about a public figure. A blunt ban on
#: the WORD would fire on that legitimate instruction, which is the same trap
#: `_AGE_ARITHMETIC` above is shaped to avoid. So the ban is on TRANSPORT: on
#: this project fetching, attaching or encoding a picture and putting it in
#: front of a model.
_RUBRIC_PROSE = ("rubrics/person/PERSON.md", "rubrics/pairing/PAIRING.md")

_IMAGE_TRANSPORT = re.compile(
    r"data:image/|base64|image_url|\bimage_b64\b|\battach(ment)?s?\b|"
    r"\b(fetch|download|upload|encode|embed)\w*[ _-]*(the[ _-]*)?"
    r"(image|photo|picture|headshot|portrait)\b|"
    r"\b(image|photo|picture|headshot|portrait)[ _-]*(url|uri|path|file|bytes|data)\b",
    re.I,
)

#: An age term doing arithmetic. Deliberately about ARITHMETIC, not about the
#: word: the rubric must be free to TELL the judge not to use an age rule, and a
#: ban that fired on its own prohibition would be useless.
_AGE_ARITHMETIC = re.compile(
    r"\bage\s*[-+*/]|\b[-+*/]\s*age\b|\bage\s*=|\bbirth_?year\b|\bdecline\s*\(|"
    r"\bage_penalty\b|\bage_curve\b|\byears_since\b",
    re.I,
)


def test_no_file_in_the_scoring_path_does_arithmetic_with_age():
    offenders = []
    for rel in _SCORING_PATH:
        p = REPO / rel
        assert p.exists(), f"{rel} is gone; this test is guarding nothing"
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if _AGE_ARITHMETIC.search(line):
                offenders.append(f"{rel}:{i}: {line.strip()}")
    assert not offenders, (
        "age arithmetic in the scoring path:\n  " + "\n  ".join(offenders)
        + "\nPlan v4 §2 keeps v3's ban on an automatic age-decline formula.")


def test_the_scorer_never_reads_a_birth_date():
    """The stronger check: the score path must not even have the input.

    A formula needs an age, an age needs a birth date, and the pairing slice
    deliberately carries neither. Roster records DO hold birth dates, for the
    adult-window filter, and that is a different pipeline stage.
    """
    for rel in ("scripts/score_pairings.py", "modules/pairing/judge.py"):
        src = (REPO / rel).read_text()
        for token in ("date_of_birth", "birth_date", "born"):
            assert token not in src, f"{rel} reads {token}"


def test_the_rubric_still_forbids_an_age_rule_in_words():
    # The code ban and the prompt ban are different guarantees. Code cannot stop
    # a judge applying its own mental formula; only the prompt can ask it not to.
    rubric = (REPO / "rubrics/pairing/PAIRING.md").read_text()
    assert "Do not apply an age rule" in rubric
    assert "no formula here" in rubric


def test_no_image_is_fetched_or_sent_to_a_judge():
    """The other half of the constraint plan v4 keeps: no face or body analysis.

    The judge works from what it already knows. Nothing fetches, attaches or
    references an image anywhere in the scoring path.
    """
    for rel in _SCORING_PATH:
        src = (REPO / rel).read_text().lower()
        for token in ("image", "photo", "jpg", "png", "base64", "vision"):
            assert token not in src, f"{rel} mentions {token}"



def test_the_current_person_scorer_is_also_image_free():
    """The live path, not just the superseded one.

    `_SCORING_PATH` predates plan v4. Every person-year in
    `data/roster100/run/person_gradings.json` was produced by
    `score_person_periods.py`, which none of the checks above ever opened.
    """
    for rel in _PERSON_SCORING_PATH:
        src = (REPO / rel).read_text().lower()
        for token in ("image", "photo", "jpg", "png", "base64", "vision"):
            assert token not in src, f"{rel} mentions {token}"


def test_no_rubric_asks_for_a_picture_to_be_transported():
    """The rubric may name photographs; it may not ask for one to be sent."""
    for rel in _RUBRIC_PROSE:
        hit = _IMAGE_TRANSPORT.search((REPO / rel).read_text())
        assert hit is None, f"{rel} looks like it moves an image: {hit.group(0)!r}"


def test_the_transport_ban_has_teeth():
    """A regex that matches nothing would pass the test above forever."""
    for bad in ("data:image/png;base64,AAAA",
                "attach the headshot",
                "image_url",
                "download the photo first",
                "portrait_bytes"):
        assert _IMAGE_TRANSPORT.search(bad), f"transport ban missed {bad!r}"

    for fine in ("their photographs, appearances, magazine coverage",
                 "how they looked in one production"):
        assert not _IMAGE_TRANSPORT.search(fine), f"transport ban fired on {fine!r}"
