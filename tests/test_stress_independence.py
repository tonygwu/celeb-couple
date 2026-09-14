"""A stress fixture must not reuse the rubric's calibration text.

S2's prose arm is the VERBATIM text of calibration Example 3, which the rubric
anchors at 88, and its award arm has the shape of Example 1, anchored at 92.
The judge returned 92, 92, 88. The case therefore measures whether the judge
follows its anchors, and cannot measure whether identical substance is
perceived differently in different formats — the rubric already told it those
two formats sit four points apart.

That went unnoticed for hours and was quoted in the report as controlled
evidence about format. This catches the next one.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

#: Known overlap, filed in docs/BACKLOG.md for redesign. Listed so the guard
#: stays useful rather than being switched off wholesale.
KNOWN_OVERLAP = {
    "the most beautiful face in the room, and everybody in the room knew it",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _fixture_strings() -> set[str]:
    """Quoted fixture text with enough WORDS to be a real phrase.

    Length alone was not enough: a 25-character run of whitespace and a comma
    normalises to "," which appears in every document, so the guard's first
    run flagged punctuation.
    """
    src = (REPO / "modules/consensus/stress.py").read_text()
    out = set(re.findall(r'"([^"]{25,})"', src))
    out |= set(re.findall(r"'([^']{25,})'", src))
    return {q for q in out if len(re.findall(r"[A-Za-z]{3,}", q)) >= 5}


def test_no_new_stress_fixture_reuses_calibration_text():
    rubric = _norm((REPO / "rubrics/standing/RUBRIC.md").read_text())
    overlap = {q for q in _fixture_strings() if _norm(q) in rubric}
    unexpected = {q for q in overlap if _norm(q) not in {_norm(k) for k in KNOWN_OVERLAP}}
    assert not unexpected, (
        "stress fixtures reusing the rubric's calibration text measure "
        "anchor-following rather than what they claim to test:\n  "
        + "\n  ".join(sorted(unexpected)))


def test_the_known_overlap_is_still_there_or_the_allowlist_is_stale():
    """When S2 is rebuilt with independent prose, this fails — which is the
    signal to drop the entry and the report text explaining it."""
    rubric = _norm((REPO / "rubrics/standing/RUBRIC.md").read_text())
    present = {k for k in KNOWN_OVERLAP if _norm(k) in rubric
               and any(_norm(k) == _norm(q) for q in _fixture_strings())}
    assert present == KNOWN_OVERLAP, (
        "the allowlisted overlap is gone; remove it from KNOWN_OVERLAP and "
        "drop the report's explanation of it"
    )


def test_the_guard_would_catch_a_new_overlap():
    """Verified to FIRE, not merely to pass: a guard only ever run against a
    clean repository proves nothing."""
    rubric = _norm("Example 9. The text reads 'a face that stopped the room'.")
    fixtures = {"a face that stopped the room, unmistakably"}
    overlap = {q for q in fixtures if _norm(q) in rubric}
    assert overlap == set(), "sanity: this one should not match"
    fixtures = {"a face that stopped the room"}
    overlap = {q for q in fixtures if _norm(q) in rubric}
    assert overlap, "the matching logic must find a contained phrase"


# -- the case set itself -----------------------------------------------------

def _cases():
    import importlib.util
    import sys as _sys
    spec = importlib.util.spec_from_file_location(
        "stress_mod", REPO / "modules/consensus/stress.py")
    m = importlib.util.module_from_spec(spec)
    _sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    # CASES is a tuple, not a list -- the first version looked only at lists
    # and found nothing, so every test below passed vacuously on an empty set.
    return list(m.CASES)


#: The plan's section 6.3 lists eight live measurement evaluations. Each maps
#: to one case. A case quietly dropped would remove a check the plan requires
#: and leave the report reporting on seven.
EXPECTED = {
    "S1_single_vs_multi": "strong single-source vs weaker multi-source",
    "S2_format_equivalence": "award vs rank vs prose",
    "S3_corroboration_no_new_judgment": "corroboration with no new judgment",
    "S4_contradiction": "contradictory evidence",
    "S5_empty_and_offtopic": "empty and generic dossiers",
    "S6_identity_leakage": "identity leakage",
    "S7_order_sensitivity": "order sensitivity",
    "S8_volume_without_content": "volume without independent content",
}


def test_all_eight_plan_cases_are_defined():
    have = {c.case_id for c in _cases()}
    missing = sorted(set(EXPECTED) - have)
    assert not missing, f"the plan requires these and they are not defined: {missing}"


def test_no_case_is_defined_twice():
    ids = [c.case_id for c in _cases()]
    assert len(ids) == len(set(ids)), ids


def test_every_case_states_what_it_expects():
    """A case with no stated expectation cannot be read as passed or failed by
    anyone who did not write it."""
    thin = [c.case_id for c in _cases()
            if not (c.expectation or "").strip()
            or len((c.expectation or "").split()) < 8]
    assert not thin, f"cases with no usable expectation: {thin}"


def test_every_case_has_at_least_two_arms_to_compare():
    """Except the ones that test a single required OUTCOME rather than a
    difference between arms."""
    single_outcome = {"S4_contradiction", "S5_empty_and_offtopic"}
    thin = [c.case_id for c in _cases()
            if len(c.arms) < 2 and c.case_id not in single_outcome]
    assert not thin, f"cases with nothing to compare: {thin}"
