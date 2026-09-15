"""`effort_took_effect` is an unexplained signal, never proof of mis-service.

The CodexJudge class docstring used to say a zero `reasoning_output_tokens`
count meant "the request was not served as asked". The measurement note beside
the field says the opposite and is the one backed by evidence: turns of 234-257
output tokens reported zero while an identical-shaped probe reported 27, so the
count cannot separate "effort did not take effect" from "this turn needed little
reasoning".

The contradiction cost something. On 2026-09-14 an analysis read the docstring,
found 18 of 40 astra verdicts flagged, and reported that nearly half the
cross-family comparison had been mis-served. That had not been shown.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

JUDGES = REPO / "packages/llmkit/judges.py"


def test_the_docstring_does_not_claim_the_flag_proves_mis_service():
    import packages.llmkit.judges as j
    # Whitespace-normalised: the docstring is wrapped, so "used to say" is
    # stored as "used to\n    say" and a raw substring check misses it. That
    # is how this test failed on its second run.
    doc = " ".join((j.CodexJudge.__doc__ or "").split())
    assert "IS NOT AN IDENTITY CHECK" in doc, (
        "CodexJudge's docstring no longer carries the disclaimer. If it has gone "
        "back to claiming the flag proves a request was not served as asked, the "
        "measurement note in __call__ contradicts it.")
    # The retracted claim may legitimately APPEAR in the docstring, because the
    # docstring quotes it in order to retract it. A bare substring ban fails on
    # the retraction itself, which it did on this test's first run. What must
    # hold is that the phrase never stands unqualified: every occurrence sits
    # after the marker that disowns it.
    if "not served as asked" in doc:
        assert "used to say" in doc, doc
        assert doc.index("used to say") < doc.index("not served as asked"), doc


def test_nothing_treats_the_flag_as_fatal():
    """It is RECORDED, never fatal. A raise or a filter on it would discard
    valid answers -- which is exactly what an earlier attempt did, throwing away
    two correct "unscored" verdicts from empty dossiers."""
    src = JUDGES.read_text()
    for line in src.splitlines():
        stripped = line.strip()
        if stripped.startswith("#") or "effort_took_effect" not in stripped:
            continue
        assert not stripped.startswith("raise"), stripped
        assert not re.match(r"if\s+not\s+effort_took_effect", stripped), stripped


def test_the_measurement_note_survives():
    # The note is the only record of WHY the flag cannot be read as a verdict.
    # Losing it would leave the disclaimer asserted with nothing behind it.
    src = JUDGES.read_text()
    assert "234-257" in src and "reported 27" in src, (
        "the measurement behind the disclaimer is gone from judges.py")
