"""A rubric must not show an example that its own rules forbid.

MENTIONS.md rule 3 says "Never infer a year. If the sentence does not carry
one, skip it." Its "What to extract" list contained *"voted the sexiest man in
a readers' poll"*, which carries no year. A judge following the examples and a
judge following the rules would disagree about that one, and there is no way to
tell from the output which it followed. Filed as W109, fixed 2026-09-14 at the
contract bump, because editing the rubric changes the contract id.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
MENTIONS = REPO / "rubrics/mentions/MENTIONS.md"

#: A four-digit year, or a decade like "1990s". The rubric also accepts a year
#: "clearly implied by the sentence", which no regex can judge, so an example
#: relying on that must say so in its own parenthetical -- as the People's 50
#: Most Beautiful example does.
_YEAR = re.compile(r"\b(19|20)\d{2}s?\b")
_IMPLIED = re.compile(r"with a year", re.I)


def _section(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    start = next(i for i, l in enumerate(lines) if l.strip() == heading)
    out = []
    for l in lines[start + 1:]:
        if l.startswith("## "):
            break
        if l.strip().startswith("- "):
            out.append(l.strip()[2:])
    return out


def test_the_section_is_found_and_non_empty():
    # Guards against a renamed heading turning the real test into a no-op.
    items = _section(MENTIONS.read_text(), "## What to extract")
    assert len(items) >= 4, items


def test_every_extraction_example_carries_a_year():
    offenders = [x for x in _section(MENTIONS.read_text(), "## What to extract")
                 if not _YEAR.search(x) and not _IMPLIED.search(x)]
    assert not offenders, (
        "MENTIONS.md rule 3 says to skip a sentence that carries no year, but "
        f"these examples under 'What to extract' carry none: {offenders}"
    )


def test_rule_three_still_says_what_this_test_assumes():
    # If the rule is ever relaxed, this test is measuring the wrong thing and
    # should fail loudly rather than keep enforcing a rule that is gone.
    assert "Never infer a year" in MENTIONS.read_text()
