"""Every new grading records WHICH model produced it and WHEN.

Gradings are now averaged across models, so a score with no model attached
cannot be excluded, re-weighted, or explained later. The 430 entries written
before 2026-09-16 have neither field, and that is exactly the gap this guard
exists to stop widening.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from modules.pairing.canonical import MODEL_FOR_FAMILY, normalise_grading

REPO = Path(__file__).resolve().parent.parent
SCORER = REPO / "scripts/score_person_periods.py"


def test_the_scorer_stamps_the_model_and_the_time():
    src = SCORER.read_text()
    assert '"model": model_for(j)' in src, (
        "the cache entry must record which model produced the score")
    assert '"graded_at_utc"' in src, "the cache entry must record when"


def test_the_scorer_never_backfills_a_time_from_the_filesystem():
    """mtime is when a file was touched, not when a judgment was made. This
    repository has paid for that confusion twice."""
    src = SCORER.read_text()
    for banned in ("st_mtime", "getmtime", "stat().st_", "os.path.getctime"):
        assert banned not in src, f"{banned} must not decide a grading time"


def test_the_scorer_parses_and_defines_its_model_resolver():
    tree = ast.parse(SCORER.read_text())
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "model_for" in names, (
        "--judges and --model must not be able to disagree silently")


def test_every_default_judge_family_has_a_pinned_model():
    """--judges defaults to opus; a family with no pinned model would make the
    script exit rather than grade, and only at the moment of spending."""
    for family in ("fable", "astra", "opus", "sonnet"):
        assert family in MODEL_FOR_FAMILY


def test_the_scorer_defaults_to_opus_not_fable():
    """Fable has a separate, scarcer weekly window, and Opus measured inside
    Fable's own run-to-run noise on the person-year task."""
    src = SCORER.read_text()
    assert 'ap.add_argument("--judges", default="opus"' in src


@pytest.mark.parametrize("family,model", sorted(MODEL_FOR_FAMILY.items()))
def test_a_grading_round_trips_its_model(family, model):
    g = normalise_grading({"person_id": "Q1", "period": "2006", "family": family,
                           "judged": True, "score": 9.0}, source="t")
    assert g["model"] == model
