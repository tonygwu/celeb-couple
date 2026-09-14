"""The generated report must DERIVE its prose claims, not assert them.

Measured 2026-09-14: after the Wikidata-label fix grew the corpus from 34 to 39
person-periods, `docs/M0-REPORT.md` still said "Every scored person-period
carries exactly one observation, and every one of those observations is a
one-winner editorial award." Both halves were false. Two person-periods carried
two observations, and the corpus held 17 ordered ranks and 4 unordered
inclusions alongside the 20 awards.

The generator's header promises "Every number below is read from a JSON
artifact, not typed." That promise covered the numbers and not the sentences
around them, which is the same defect wearing a different hat: a claim nobody
recomputed when the inputs moved.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _gen():
    spec = importlib.util.spec_from_file_location(
        "write_m0_report", REPO / "scripts/write_m0_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MIXED = {
    "by_shape": {
        "editorial_award": {"n": 18, "mean": 91.28, "min": 78.0, "max": 94.0,
                            "sd": 3.263},
        "ordered_rank": {"n": 16, "mean": 84.56, "min": 64.0, "max": 93.0,
                         "sd": 6.727},
        "unordered_inclusion": {"n": 3, "mean": 80.67, "min": 76.0, "max": 86.0,
                                "sd": 4.11},
    }
}
MIXED_DENSITY = {"distribution": {"1": 37, "2": 2}, "person_periods": 39}

SINGLE = {"by_shape": {"editorial_award": {"n": 12, "mean": 92.0, "min": 92.0,
                                           "max": 92.0, "sd": 0.0}}}
SINGLE_DENSITY = {"distribution": {"1": 12}, "person_periods": 12}


def test_it_does_not_claim_a_single_shape_when_the_corpus_holds_three():
    text = _gen().shape_paragraph(MIXED, MIXED_DENSITY)
    low = text.lower()
    assert "every one of those observations" not in low
    assert "exactly one observation" not in low, (
        "two person-periods carry two observations in this fixture"
    )
    for shape in ("editorial_award", "ordered_rank", "unordered_inclusion"):
        assert shape in text, f"{shape} is in the corpus and must be named"


def test_it_reports_the_real_counts_and_spreads():
    text = _gen().shape_paragraph(MIXED, MIXED_DENSITY)
    for n in ("18", "16", "3", "78.0", "94.0", "64.0", "93.0"):
        assert n in text, f"{n} comes straight from by_shape and must appear"


def test_a_genuinely_uniform_corpus_is_still_described_as_uniform():
    """The old sentence was not wrong when it was written. It stopped being
    true. A corpus that really does hold one shape must still say so."""
    text = _gen().shape_paragraph(SINGLE, SINGLE_DENSITY)
    assert "editorial_award" in text
    assert "ordered_rank" not in text


def test_it_says_how_many_person_periods_carry_more_than_one_observation():
    assert "2 of 39" in _gen().shape_paragraph(MIXED, MIXED_DENSITY)
    assert "every" in _gen().shape_paragraph(SINGLE, SINGLE_DENSITY).lower()


def test_the_committed_report_matches_the_committed_artifacts():
    """Optional: only runs in a clone that has produced the artifacts."""
    import json
    conf = REPO / "data/pilot/run/shape_confound.json"
    dens = REPO / "data/pilot/run/evidence_density.json"
    if not (conf.exists() and dens.exists()):
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")
    para = _gen().shape_paragraph(json.loads(conf.read_text()),
                                  json.loads(dens.read_text()))
    report = (REPO / "docs/M0-REPORT.md").read_text()
    assert para in report, "docs/M0-REPORT.md is stale; re-run write_m0_report.py"
