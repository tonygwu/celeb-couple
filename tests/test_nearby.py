from __future__ import annotations

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
