"""The trap verifier has to FAIL when the trap breaks.

A checker that always passes is indistinguishable from a checker that works,
right up until the moment it matters. Every claim here is tested in both
directions against fixtures, because the real artifacts currently satisfy all
three and cannot demonstrate the failing branch.

Breaking any of these claims would be good news for the project. That is the
point: the capstone says "there are no exceptions in the corpus", and a
document nobody re-derives keeps saying it long after it stops being true.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "verify_trap", REPO / "scripts/verify_trap.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _fixtures(*, comparable_gap=0.0, mismatched_gap=-6.0, male_ranked=0):
    joint = {"jointly_covered": [
        {"a": "A1", "b": "B1", "period": "2003", "domain": "on_screen",
         "comparability": "comparable"},
        {"a": "A2", "b": "B2", "period": "1999", "domain": "real_life",
         "comparability": "shape_mismatched"},
    ]}
    shape = {"rows": [
        {"person": "A1", "period": "2003", "estimate": 92.0, "shape": "editorial_award"},
        {"person": "B1", "period": "2003", "estimate": 92.0 - comparable_gap,
         "shape": "editorial_award"},
        {"person": "A2", "period": "1999", "estimate": 92.0, "shape": "editorial_award"},
        {"person": "B2", "period": "1999", "estimate": 92.0 - mismatched_gap,
         "shape": "ordered_rank"},
    ]}
    gsc = {"ranked_observations": {"male": male_ranked, "female": 17}}
    return joint, shape, gsc


def _by_claim(results):
    return {r["claim"]: r for r in results}


def test_the_current_fixtures_satisfy_every_claim():
    mod = _mod()
    assert all(r["holds"] for r in mod.check(*_fixtures()))


def test_a_comparable_pairing_with_a_real_gap_breaks_the_first_claim():
    mod = _mod()
    r = _by_claim(mod.check(*_fixtures(comparable_gap=4.0)))
    first = r["every shape-comparable pairing has a gap of exactly 0.0"]
    assert first["holds"] is False
    assert first["exceptions"], "a broken claim must name the exception"
    assert "first real signal" in first["if_broken"]


def test_a_nonzero_gap_that_is_comparable_breaks_the_second_claim():
    """The two claims overlap on purpose: this fixture trips both, and a reader
    must see both rather than the first one masking the second."""
    mod = _mod()
    results = mod.check(*_fixtures(comparable_gap=4.0))
    broken = [r["claim"] for r in results if not r["holds"]]
    assert len(broken) == 2, broken


def test_a_ranked_observation_for_a_man_breaks_the_third_claim():
    mod = _mod()
    r = _by_claim(mod.check(*_fixtures(male_ranked=3)))
    third = r["men hold zero ranked observations"]
    assert third["holds"] is False
    assert "3 ranked observations" in third["exceptions"][0]


def test_a_reused_nearby_estimate_is_resolved_not_dropped():
    """`a_src`/`b_src` name the period the estimate was made for, which differs
    from the pairing period under bounded reuse. Keying on the pairing period
    would silently drop the row and report fewer checks while still passing."""
    mod = _mod()
    joint = {"jointly_covered": [
        {"a": "A", "b": "B", "period": "2001", "domain": "real_life",
         "comparability": "shape_mismatched", "a_src": "2000", "b_src": "2000"}]}
    shape = {"rows": [
        {"person": "A", "period": "2000", "estimate": 92.0, "shape": "editorial_award"},
        {"person": "B", "period": "2000", "estimate": 78.0, "shape": "ordered_rank"}]}
    results = mod.check(joint, shape, {"ranked_observations": {"male": 0}})
    second = _by_claim(results)["every non-zero gap is shape-mismatched"]
    assert second["checked"] == 1, "the reused estimate must resolve"


def test_an_unresolvable_pairing_is_not_counted_as_passing():
    """A pairing whose estimate cannot be found must not silently count as a
    zero gap, which would make the first claim pass for the wrong reason."""
    mod = _mod()
    joint = {"jointly_covered": [
        {"a": "A", "b": "MISSING", "period": "2003", "domain": "on_screen",
         "comparability": "comparable"}]}
    shape = {"rows": [{"person": "A", "period": "2003", "estimate": 92.0,
                       "shape": "editorial_award"}]}
    results = mod.check(joint, shape, {"ranked_observations": {"male": 0}})
    first = _by_claim(results)["every shape-comparable pairing has a gap of exactly 0.0"]
    assert first["checked"] == 0, "an unresolved pairing is not evidence"


def test_the_real_corpus_still_satisfies_the_capstone():
    """Optional: needs the artifacts, which live under a gitignored data/."""
    import json
    paths = ["data/pilot/run/joint_with_nearby.json",
             "data/pilot/run/shape_confound.json",
             "data/pilot/run/gender_shape_confound.json"]
    if not all((REPO / p).exists() for p in paths):
        pytest.skip("data/ is gitignored; nothing to verify in a fresh clone")
    mod = _mod()
    results = mod.check(*[json.loads((REPO / p).read_text()) for p in paths])
    broken = [r for r in results if not r["holds"]]
    assert not broken, (
        "docs/THE-TRAP.md states these as absolute:\n"
        + "\n".join(f"  {r['claim']}: {r['exceptions']}" for r in broken))


# -- cross-run estimate extraction -------------------------------------------

def _xrun():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cross_run_stability", REPO / "scripts/cross_run_stability.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def test_two_estimates_for_one_person_period_are_refused():
    """A pairings file lists the same person under several pairings. A plain
    assignment kept whichever came last, so an inconsistent artifact would have
    produced a stability figure built on an arbitrary pick."""
    mod = _xrun()
    payload = {"pairings": [
        {"a": "X", "a_from": "2000", "a_estimate": 92.0,
         "b": "Y", "b_from": "2000", "b_estimate": 80.0},
        {"a": "X", "a_from": "2000", "a_estimate": 88.0,
         "b": "Z", "b_from": "2001", "b_estimate": 70.0},
    ]}
    with pytest.raises(ValueError, match="two different estimates"):
        mod.estimates(payload)


def test_the_same_estimate_repeated_is_fine():
    mod = _xrun()
    payload = {"pairings": [
        {"a": "X", "a_from": "2000", "a_estimate": 92.0,
         "b": "Y", "b_from": "2000", "b_estimate": 80.0},
        {"a": "X", "a_from": "2000", "a_estimate": 92.0,
         "b": "Z", "b_from": "2001", "b_estimate": 70.0},
    ]}
    assert mod.estimates(payload)[("X", "2000")] == 92.0


def test_an_unrecognised_score_artifact_raises_rather_than_returning_empty():
    """An empty dict here reads as 'the two runs agree perfectly'."""
    mod = _xrun()
    with pytest.raises(ValueError, match="unrecognised"):
        mod.estimates({"something_else": []})


# -- robustness of the conclusions to methodological choices -----------------

def _robust():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "conclusion_robustness", REPO / "scripts/conclusion_robustness.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def test_a_tighter_bound_can_only_reduce_joint_coverage():
    """Monotonicity is the property that makes the sweep meaningful: if a
    smaller bound admitted MORE pairings, the dial would not be doing what the
    document says it does."""
    import json
    f = REPO / "data/pilot/run/conclusion_robustness.json"
    if not f.exists():
        pytest.skip("data/ is gitignored; nothing to check in a fresh clone")
    settings = json.loads(f.read_text())["settings"]
    # A sorted() check over an empty list is vacuously true, so the sweep has
    # to be shown to exist before its monotonicity means anything.
    assert len(settings) >= 4, f"the bound sweep is too small to test: {settings}"
    for rf in (True, False):
        series = [s for s in settings if s["romance_filter"] is rf]
        assert len(series) >= 2, f"no sweep at romance_filter={rf}"
        series.sort(key=lambda s: s["bound"])
        covered = [s["jointly_covered"] for s in series]
        assert covered == sorted(covered), (
            f"joint coverage is not monotonic in the bound at "
            f"romance_filter={rf}: {covered}")


def test_the_romance_filter_only_ever_removes_pairings():
    import json
    f = REPO / "data/pilot/run/conclusion_robustness.json"
    if not f.exists():
        pytest.skip("data/ is gitignored")
    settings = {(s["bound"], s["romance_filter"]): s
                for s in json.loads(f.read_text())["settings"]}
    assert any(rf for _, rf in settings), (
        "no romance-filtered setting, so this asserts nothing about the filter")
    for (bound, rf), s in settings.items():
        if rf:
            other = settings.get((bound, False))
            assert other is None or s["jointly_covered"] <= other["jointly_covered"]


def test_the_claims_hold_at_the_settings_the_project_actually_uses():
    """Bound 1 with the romance filter on. If the conclusions failed there, the
    capstone would be wrong rather than merely dial-dependent."""
    import json
    f = REPO / "data/pilot/run/conclusion_robustness.json"
    if not f.exists():
        pytest.skip("data/ is gitignored")
    live = next(s for s in json.loads(f.read_text())["settings"]
                if s["bound"] == 1 and s["romance_filter"] is True)
    assert live["comparable_with_a_nonzero_gap"] == 0
    assert (live["nonzero_gaps_that_are_shape_mismatched"]
            == live["nonzero_gaps_total"])
