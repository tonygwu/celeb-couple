from __future__ import annotations

from fractions import Fraction as F

from modules.analytics.metrics import Pairing, PeriodExposure, as_estimate
from modules.analytics.qualification import (
    MAX_SHARE_NEARBY_REUSE, MIN_JOINT_COVERAGE, PARTIAL_TOTAL_DISCLOSURE, qualify,
)


def _k(pid, period="2016", f=80.0, p=90.0, fid="se_f", pid_="se_p", w=F(1)):
    return Pairing(pid, "a", "b", "on_screen",
                   (PeriodExposure(period, F(1), as_estimate(f), as_estimate(p),
                                   fid, pid_),), w)


DAY = {"2016": "day", "2017": "day", "2018": "day", "2019": "day"}
MULTI = {f"f{i}": "multi_publisher" for i in range(6)}


def test_a_full_profile_qualifies():
    ks = [_k(f"f{i}", period=str(2016 + i)) for i in range(3)]
    q = qualify("p1", "on_screen", ks, support_levels=MULTI, period_precision=DAY)
    assert q.ranked is True and q.reasons == ()
    assert q.disclosure is None, "full coverage needs no partial-total disclosure"


def test_too_few_scored_films_leaves_the_profile_unranked_but_visible():
    ks = [_k("f0"), _k("f1", period="2017")]
    q = qualify("p1", "on_screen", ks, support_levels=MULTI, period_precision=DAY)
    assert q.ranked is False
    assert any("needs 3" in r for r in q.reasons)
    assert q.scored_pairings == 2, "the records are still counted and shown"


def test_low_joint_coverage_disqualifies():
    scored = [_k(f"f{i}", period=str(2016 + i)) for i in range(3)]
    unscored = [Pairing(f"u{i}", "a", "b", "on_screen",
                        (PeriodExposure("2020", F(1), as_estimate(80.0), None,
                                        "se_f", None),), F(1))
                for i in range(5)]
    q = qualify("p1", "on_screen", scored + unscored,
                support_levels=MULTI, period_precision=DAY)
    assert q.joint_coverage < MIN_JOINT_COVERAGE
    assert q.ranked is False
    assert any("joint coverage" in r for r in q.reasons)


def test_partial_coverage_always_carries_the_not_a_lower_bound_sentence():
    scored = [_k(f"f{i}", period=str(2016 + i)) for i in range(3)]
    unscored = [Pairing("u", "a", "b", "on_screen",
                        (PeriodExposure("2020", F(1), as_estimate(80.0), None,
                                        "se_f", None),), F(1))]
    q = qualify("p1", "on_screen", scored + unscored,
                support_levels=MULTI, period_precision=DAY)
    assert q.disclosure == PARTIAL_TOTAL_DISCLOSURE
    assert "not a conservative lower bound" in q.disclosure
    assert "above or below" in q.disclosure


def test_single_source_films_alone_cannot_carry_a_rank():
    ks = [_k(f"f{i}", period=str(2016 + i)) for i in range(3)]
    q = qualify("p1", "on_screen", ks,
                support_levels={f"f{i}": "single_source" for i in range(3)},
                period_precision=DAY)
    assert q.ranked is False
    assert any("single source" in r for r in q.reasons)


def test_year_precision_exposure_disqualifies_without_the_sensitivity_shown():
    ks = [_k(f"f{i}", period=str(2016 + i)) for i in range(3)]
    q = qualify("p1", "on_screen", ks, support_levels=MULTI,
                period_precision={str(2016 + i): "year" for i in range(3)})
    assert q.ranked is False
    assert any("month-precision" in r for r in q.reasons)


def test_too_much_nearby_period_reuse_disqualifies():
    ks = [_k(f"f{i}", period=str(2016 + i), fid=f"se_{i}") for i in range(3)]
    q = qualify("p1", "on_screen", ks, support_levels=MULTI, period_precision=DAY,
                # The partner id has to be named too. This test used to supply
                # only the focal ids and lean on the permissive default, which
                # is exactly what the completeness check exists to surface.
                period_support={**{f"se_{i}": "nearby_period" for i in range(3)},
                                "se_p": "contemporaneous"})
    assert q.share_nearby_reuse > MAX_SHARE_NEARBY_REUSE
    assert q.ranked is False
    assert any("nearby-period reuse" in r for r in q.reasons)


def test_real_life_needs_two_episodes_not_three():
    ks = [Pairing(f"e{i}", "a", "b", "real_life",
                  (PeriodExposure(str(2016 + i), F(1), as_estimate(80.0),
                                  as_estimate(90.0), "se_f", "se_p"),), F(1))
          for i in range(2)]
    q = qualify("p1", "real_life", ks, period_precision=DAY)
    assert q.ranked is True


def test_every_threshold_is_a_named_constant_not_a_literal():
    import inspect
    from modules.analytics import qualification as q
    src = inspect.getsource(q.qualify)
    for literal in ("0.6", "0.5", "0.4", " 3 ", " 2 "):
        assert literal not in src.replace("MIN_", "").replace("MAX_", ""), (
            f"threshold literal {literal!r} appears inside qualify(); it belongs "
            "in a named constant so a published number cannot rest on typed prose"
        )


# -- partial metadata is an oversight, empty metadata is a statement ---------

def test_an_empty_support_map_means_no_nearby_reuse():
    """A caller with none of this metadata is making a coherent statement: no
    special cases anywhere. That stays supported."""
    ks = [_k(f"f{i}", period=str(2016 + i), fid=f"se_a{i}", pid_=f"se_b{i}")
          for i in range(3)]
    q = qualify("p", "real_life", ks, period_support={})
    assert q.share_nearby_reuse == F(0)


def test_a_partial_support_map_is_refused():
    """Absent-from-a-populated-map is an oversight, not a statement.

    `period_support.get(eid)` returning None counts the estimate as
    contemporaneous, which UNDERSTATES share_nearby_reuse -- and that share is
    compared against a CAP. Understating it is the direction that lets a
    pairing qualify when it should not. Every other default in this function
    errs the other way; this one did not.
    """
    import pytest
    ks = [_k("f0", fid="se_a", pid_="se_b")]
    with pytest.raises(ValueError, match="se_b"):
        qualify("p", "real_life", ks, period_support={"se_a": "nearby_period"})


def test_a_complete_support_map_is_accepted():
    ks = [_k("f0", fid="se_a", pid_="se_b")]
    q = qualify("p", "real_life", ks,
                period_support={"se_a": "nearby_period",
                                "se_b": "contemporaneous"})
    assert q.share_nearby_reuse == F(1)


def test_the_refusal_names_every_missing_estimate():
    import pytest
    ks = [_k("f0", fid="se_a", pid_="se_b")]
    with pytest.raises(ValueError) as e:
        qualify("p", "real_life", ks, period_support={"se_zzz": "nearby_period"})
    assert "se_a" in str(e.value) and "se_b" in str(e.value)
