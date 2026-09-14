from __future__ import annotations

from pathlib import Path

import pytest

from modules.consensus.nearby import NEARBY_BOUND_YEARS, resolve_period


def test_the_declared_bound_is_one_year():
    assert NEARBY_BOUND_YEARS == 1


def test_an_exact_match_wins_and_is_marked_contemporaneous():
    r = resolve_period("2002", {"2002": 88.0, "2001": 70.0})
    assert r.source_period == "2002" and r.distance == 0
    assert r.support == "contemporaneous"


def test_a_neighbouring_year_is_reused_and_marked_as_such():
    r = resolve_period("2001", {"2002": 88.0})
    assert r.source_period == "2002" and r.distance == 1
    assert r.support == "nearby_period"


def test_two_years_away_is_unscored_not_scored_from_the_nearest_thing():
    r = resolve_period("2004", {"2002": 88.0})
    assert r.scored is False
    assert r.support == "unscored"
    assert r.reason == "beyond_nearby_period_bound"


def test_ties_break_to_the_earlier_year_deterministically():
    a = resolve_period("2002", {"2001": 70.0, "2003": 90.0})
    b = resolve_period("2002", {"2003": 90.0, "2001": 70.0})
    assert a.source_period == b.source_period == "2001", "dict order must not decide"


def test_an_unscored_neighbour_is_not_reused():
    r = resolve_period("2001", {"2002": None})
    assert r.scored is False


def test_reuse_carries_the_source_period_so_one_estimate_keeps_one_identity():
    """Three period keys served by one 2002 estimate must name that estimate."""
    resolutions = [resolve_period(y, {"2002": 88.0}) for y in ("2001", "2002", "2003")]
    assert [r.source_period for r in resolutions] == ["2002", "2002", "2002"]
    assert len({r.source_period for r in resolutions}) == 1, (
        "one source estimate, so the simulation draws it once rather than three times"
    )


def test_the_alignment_report_takes_its_bound_from_the_constant():
    """`"current_bound": 1` was typed into the artifact the M0 report reads,
    and two console labels hardcoded it as well. The declared bound lives in
    one place; anything that repeats it labels the wrong row the day it
    changes, and the report would state a bound the pipeline did not use."""
    src = (Path(__file__).resolve().parent.parent
           / "scripts/alignment_gap.py").read_text()
    assert '"current_bound": 1' not in src
    assert "NEARBY_BOUND_YEARS" in src


def test_the_live_artifact_agrees_with_the_constant():
    import json
    f = (Path(__file__).resolve().parent.parent
         / "data/pilot/run/alignment_gap.json")
    if not f.exists():
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")
    assert json.loads(f.read_text())["current_bound"] == NEARBY_BOUND_YEARS


def test_the_source_simulation_lists_distinct_names():
    """The simulation drew its annual list with `rng.choices`, which samples
    WITH replacement, and then deduped. A rung labelled "100 names per year"
    listed a median of 48 distinct people, and no rung above it listed more —
    so the curve's saturation was partly an artifact of the sampler rather than
    a property of the coverage problem.

    A published annual ranked list of 100 names contains 100 distinct people.
    """
    import importlib.util
    import random
    import sys as _sys

    repo = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "source_requirement", repo / "scripts/source_requirement.py")
    mod = importlib.util.module_from_spec(spec)
    _sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)

    rng = random.Random(1)
    pool = [f"Q{i}" for i in range(100)]
    weights = {q: 1.0 / (i + 3) for i, q in enumerate(pool)}
    for k in (10, 25, 50, 100):
        picked = mod._weighted_sample_without_replacement(pool, weights, k, rng)
        assert len(picked) == k, f"asked for {k} names, listed {len(picked)}"
        assert len(set(picked)) == k, "the names must be distinct"


def test_asking_for_more_names_than_the_pool_returns_the_pool():
    import importlib.util
    import random
    import sys as _sys
    repo = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "source_requirement", repo / "scripts/source_requirement.py")
    mod = importlib.util.module_from_spec(spec)
    _sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    pool = ["Q1", "Q2", "Q3"]
    weights = {q: 1.0 for q in pool}
    got = mod._weighted_sample_without_replacement(pool, weights, 99, random.Random(1))
    assert sorted(got) == sorted(pool), (
        "a list deeper than the roster lists the whole roster; that is what "
        "makes the saturation real rather than a sampling limit"
    )
