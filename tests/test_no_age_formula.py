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

#: Everything that can touch a pairing score.
_SCORING_PATH = (
    "scripts/score_pairings.py",
    "scripts/select_m1_slice.py",
    "modules/pairing/judge.py",
    "rubrics/pairing/PAIRING.md",
    "rubrics/pairing/pairing.schema.json",
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
