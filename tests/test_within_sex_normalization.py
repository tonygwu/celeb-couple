"""What within-sex normalization must do, and what it must not quietly do.

The normalized board is a SECOND view beside the raw one, the way plan v3's
`same_shape_view` sat beside the main board. These tests pin the four things
that make it readable as a scenario rather than as a correction:

1. the population is (sex, person, period) tuples, so a person judged in three
   periods is three observations and a person judged five times in ONE period
   is still one;
2. the normalized populations of the two sexes have the same mean and the same
   spread, exactly, which is the whole construction;
3. the mean normalized gap is therefore about zero -- that is the point AND the
   cost, because the view can no longer answer "do the judges score women
   higher"; it assumes the answer is no;
4. full normalization CAN reorder the rate board, unlike the constant offset in
   tests/test_offset_invariance.py, because it rescales as well as shifts.
"""

from __future__ import annotations

import json
import sys
from fractions import Fraction
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from modules.pairing.boards import build_board  # noqa: E402
from modules.pairing.normalize import (  # noqa: E402
    NotNormalizable, load_raw_verdicts, normalize_population, normalized_gaps,
    normalized_records, observations, population, rank_changes, scales,
)


def _v(pid, fam, m, w, period, m_abs, f_abs):
    return {"family": fam, "pairing_id": pid, "male_qid": m, "female_qid": w,
            "period": period, "m_absolute": m_abs, "f_absolute": f_abs}


# --------------------------------------------------------------------------
# 1. The population is (sex, person, period), not one score per person.
# --------------------------------------------------------------------------

def test_a_person_judged_in_three_periods_is_three_observations():
    vs = [
        _v("p1", "astra", "M1", "W1", "1999", "8.0", "9.0"),
        _v("p2", "astra", "M1", "W2", "2004", "8.4", "9.0"),
        _v("p3", "astra", "M1", "W3", "2011", "8.8", "9.0"),
    ]
    pop = population(observations(vs))
    mine = {k: v for k, v in pop.items() if k[1:3] == ("male", "M1")}
    assert sorted(k[3] for k in mine) == ["1999", "2004", "2011"]
    assert len(mine) == 3


def test_a_person_judged_five_times_in_one_period_is_still_one_observation():
    """The operator's rule is (Male x Time-Slice) TUPLES, so a person-period
    that turns up in five pairings gets one vote in the population, not five.
    Its score is the mean of the five, exactly."""
    vs = [_v(f"p{i}", "astra", "M1", f"W{i}", "2004", s, "9.0")
          for i, s in enumerate(["8.0", "8.2", "8.4", "8.6", "8.8"])]
    pop = population(observations(vs))
    mine = {k: v for k, v in pop.items() if k[1:3] == ("male", "M1")}
    assert len(mine) == 1
    assert next(iter(mine.values())) == Fraction("8.4")


def test_the_two_judge_families_are_separate_populations():
    """An absolute score only means something on the scale of the judge that
    produced it, and the two families do not share a scale."""
    vs = [_v("p1", "astra", "M1", "W1", "1999", "8.0", "9.0"),
          _v("p1", "fable", "M1", "W1", "1999", "8.6", "9.4")]
    pop = population(observations(vs))
    assert sorted(k[0] for k in pop) == ["astra", "astra", "fable", "fable"]
    assert len(pop) == 4


# --------------------------------------------------------------------------
# 2 and 3. What normalization makes true, which is also what it costs.
# --------------------------------------------------------------------------

def _spread_corpus():
    """Men spread wide and low, women narrow and high -- the real shape."""
    vs = []
    men = ["7.6", "8.0", "8.4", "8.8", "9.2", "9.6"]
    women = ["8.8", "9.0", "9.1", "9.2", "9.3", "9.5"]
    for i, (m, w) in enumerate(zip(men, women)):
        vs.append(_v(f"p{i}", "astra", f"M{i}", f"W{i}", "2000", m, w))
    return vs


def _mean(xs):
    xs = list(xs)
    return sum(xs, Fraction(0)) / len(xs)


def _sd(xs):
    xs = list(xs)
    mu = _mean(xs)
    return sum(((x - mu) ** 2 for x in xs), Fraction(0)) / (len(xs) - 1)


def test_the_normalized_sexes_share_a_mean_and_a_variance_exactly():
    pop = population(observations(_spread_corpus()))
    norm = normalize_population(pop)
    f = [v for k, v in norm.items() if k[1] == "female"]
    m = [v for k, v in norm.items() if k[1] == "male"]
    assert _mean(f) == _mean(m)
    # Variance is compared rather than sd: the sd is a rounded square root, so
    # only the variance is exact, and a test that claims exactness must compare
    # the quantity that actually is exact.
    assert abs(_sd(f) - _sd(m)) < Fraction(1, 10 ** 30)


def test_the_mean_normalized_gap_is_zero_by_construction():
    """The point AND the cost. Every tuple appears in exactly one pairing here,
    so the pairing-level mean is the population-level mean and comes out at
    exactly zero. The raw corpus has a mean gap of about +0.44; after this it
    has none, so the normalized view CANNOT be asked whether the judges score
    women higher. It has assumed they do not."""
    vs = _spread_corpus()
    gaps = normalized_gaps(vs)
    vals = [g["astra"] for g in gaps.values()]
    assert _mean(vals) == 0


def test_the_raw_corpus_it_is_built_from_does_have_an_offset():
    """The companion to the test above: the thing being removed is real."""
    vs = _spread_corpus()
    raw = [Fraction(v["f_absolute"]) - Fraction(v["m_absolute"]) for v in vs]
    assert _mean(raw) > Fraction(1, 4)


# --------------------------------------------------------------------------
# It is not min-max, and the tests say why that matters.
# --------------------------------------------------------------------------

def test_the_scale_is_not_pinned_to_the_extremes():
    """Min-max normalization would put every population's min at one fixed
    value and its max at another, so a single outlier would set the scale for
    everyone else. Under z-scoring the extremes move with the sample."""
    a = population(observations(_spread_corpus()))
    b = dict(a)
    # One man collapses to a far outlier. Under min-max every other man's
    # normalized score would change; under z-scoring the extremes are free.
    key = next(k for k in b if k[1] == "male")
    b[key] = Fraction("3.0")
    na, nb = normalize_population(a), normalize_population(b)
    ma = [v for k, v in na.items() if k[1] == "male"]
    mb = [v for k, v in nb.items() if k[1] == "male"]
    assert (min(ma), max(ma)) != (min(mb), max(mb))


def test_a_degenerate_cell_refuses_rather_than_defaulting():
    """Fail loud. A sex whose observations are all identical has no spread to
    divide by, and returning the raw score, or zero, would be a silent wrong
    answer."""
    vs = [_v(f"p{i}", "astra", f"M{i}", f"W{i}", "2000", "8.5", w)
          for i, w in enumerate(["9.0", "9.2", "9.4"])]
    with pytest.raises(NotNormalizable):
        normalize_population(population(observations(vs)))


def test_the_arithmetic_is_exact_not_floating_point():
    """`Fraction(str(x))`, never `Fraction(0.4)`. The mean of 8.1, 8.2 and 8.3
    is exactly 8.2, and binary floating point does not agree."""
    vs = [_v(f"p{i}", "astra", "M1", f"W{i}", "2000", s, "9.0")
          for i, s in enumerate(["8.1", "8.2", "8.3"])]
    pop = population(observations(vs))
    assert pop[("astra", "male", "M1", "2000")] == Fraction("8.2")


# --------------------------------------------------------------------------
# 4. Full normalization can do what a constant offset provably cannot.
# --------------------------------------------------------------------------

_NAMES = {"M1": "A", "M2": "B", "W1": "X", "W2": "Y", "W3": "Z", "W4": "V"}


def test_full_normalization_can_reorder_the_rate_board():
    """tests/test_offset_invariance.py proves a CONSTANT offset leaves every
    rate unchanged in order, because it moves every rate by the same delta.
    Normalization also rescales, by a different factor per sex, so it does not
    have that invariance and the rate board can reorder. This test is the
    counter-example that shows the two statements are different statements."""
    vs = [
        # The women here are packed into 0.2 points and the men are spread over
        # 1.6, which is the real corpus exaggerated. Normalization divides each
        # sex by its own spread, so a 0.1-point edge among the women becomes a
        # larger move than a 0.8-point edge among the men. A's partners are the
        # top women; B's are the bottom women. Raw, B leads on rate; once each
        # sex is measured against its own spread, A does.
        _v("pA0", "astra", "M1", "W1", "2000", "7.6", "9.4"),
        _v("pA1", "astra", "M1", "W2", "2001", "9.2", "9.4"),
        _v("pB0", "astra", "M2", "W3", "2000", "7.6", "9.2"),
        _v("pB1", "astra", "M2", "W4", "2001", "7.6", "9.2"),
    ]
    recs = [{"pairing_id": v["pairing_id"], "domain": "on_screen",
             "period": v["period"], "work": v["pairing_id"],
             "gap": float(Fraction(v["f_absolute"]) - Fraction(v["m_absolute"])),
             "centrality": 1.0,
             "male_qid": v["male_qid"], "female_qid": v["female_qid"],
             "male": _NAMES[v["male_qid"]], "female": _NAMES[v["female_qid"]]}
            for v in vs]
    norm, diag = normalized_records(recs, vs)
    assert diag["pairings_normalized"] == 4

    def order(rs, key):
        return [r["name"] for r in sorted(rs, key=lambda r: (-(r[key] or 0), r["name"]))]

    raw_rows = build_board(recs, gender="male", domain="on_screen",
                           names=_NAMES, min_pairings=1)
    n_rows = build_board(norm, gender="male", domain="on_screen",
                         names=_NAMES, min_pairings=1)
    assert order(raw_rows, "paw_rate") == ["B", "A"]
    assert order(n_rows, "paw_rate") == ["A", "B"]


def test_rank_changes_counts_movement_and_says_who_moved():
    before = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
    after = [{"name": "B"}, {"name": "A"}, {"name": "C"}]
    rc = rank_changes(before, after)
    assert rc["people"] == 3
    assert rc["moved"] == 2
    assert rc["discordant_pairs"] == 1
    assert rc["entered"] == [] and rc["left"] == []
    assert ("A", 1, 2) in [tuple(m) for m in rc["movements"]]


def test_rank_changes_reports_a_changed_membership_rather_than_hiding_it():
    before = [{"name": "A"}, {"name": "B"}]
    after = [{"name": "A"}, {"name": "C"}]
    rc = rank_changes(before, after)
    assert rc["left"] == ["B"] and rc["entered"] == ["C"]


# --------------------------------------------------------------------------
# The reader: fenced JSON, which 72 of the 262 stored verdicts are wrapped in.
# --------------------------------------------------------------------------

def test_a_fenced_verdict_is_read_not_silently_skipped(tmp_path):
    """The fable judge wraps its JSON in a ```json block. A reader that calls
    json.loads directly drops every one of those files and reports a smaller
    corpus with no error at all -- which is how the absolute means quoted for
    fable came from 57 verdicts instead of 119."""
    raw = tmp_path / "raw"
    raw.mkdir()
    body = {"schema_version": "pairing-1.0", "pairing_id": "p1", "judged": True,
            "cannot_judge_reason": None, "gap": 0.4, "f_absolute": 9.0,
            "m_absolute": 8.6, "centrality": 1.0, "reasoning": "x"}
    (raw / "p1__fable.txt").write_text("```json\n" + json.dumps(body) + "\n```")
    (raw / "p1__astra.txt").write_text(json.dumps(body))
    recs = [{"pairing_id": "p1", "male_qid": "M1", "female_qid": "W1",
             "period": "2000", "domain": "on_screen"}]
    vs = load_raw_verdicts(raw, recs)
    assert sorted(v["family"] for v in vs) == ["astra", "fable"]


def test_a_verdict_with_no_matching_record_is_reported_not_dropped(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    body = {"schema_version": "pairing-1.0", "pairing_id": "ghost", "judged": True,
            "cannot_judge_reason": None, "gap": 0.4, "f_absolute": 9.0,
            "m_absolute": 8.6, "centrality": 1.0, "reasoning": "x"}
    (raw / "ghost__astra.txt").write_text(json.dumps(body))
    with pytest.raises(NotNormalizable, match="ghost"):
        load_raw_verdicts(raw, [])


# --------------------------------------------------------------------------
# Scales are reported, never assumed.
# --------------------------------------------------------------------------

def test_every_scale_reports_the_n_it_was_computed_from():
    """n is the reason the method choice is what it is, so it travels with the
    numbers rather than being quoted once in a docstring."""
    sc = scales(population(observations(_spread_corpus())))
    assert sc[("astra", "female")].n == 6
    assert sc[("astra", "male")].n == 6
    assert sc[("astra", "*")].n == 12


# --------------------------------------------------------------------------
# The real corpus, when this clone has one. data/ is gitignored, so these skip
# in a fresh clone rather than failing it.
# --------------------------------------------------------------------------

_RUN = REPO / "data/roster100/run"


def _corpus():
    scores = [_RUN / "pairing_scores.json", _RUN / "pairing_scores_fable.json"]
    raw = _RUN / "raw_pairings"
    if not raw.is_dir() or not all(p.exists() for p in scores):
        pytest.skip("data/roster100/run absent; data/ is gitignored")
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "build_boards", REPO / "scripts/build_boards.py")
    bb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bb)
    recs, _ = bb.merge_families([json.loads(p.read_text()) for p in scores])
    return recs, load_raw_verdicts(raw, recs)


def test_normalization_removes_the_measured_offset_on_the_real_corpus():
    """The raw corpus has a mean gap around +0.43. After normalization it is
    under a hundredth of a point, which is the construction working. It is not
    exactly zero because the pairings weight the tuples unevenly: a person-period
    judged in five pairings is one observation in the population and five terms
    in this mean."""
    recs, verdicts = _corpus()
    nrecs, diag = normalized_records(recs, verdicts)
    by_id = {r["pairing_id"]: r for r in recs}
    raw = [by_id[r["pairing_id"]]["gap"] for r in nrecs if r["gap"] is not None]
    norm = [r["gap"] for r in nrecs if r["gap"] is not None]
    assert len(norm) > 50, "too few normalized pairings to mean anything"
    assert sum(raw) / len(raw) > 0.3
    assert abs(sum(norm) / len(norm)) < 0.01
    assert diag["pairings_with_a_raw_gap_but_no_normalized_gap"] == 0


def test_every_stored_verdict_is_read_including_the_fenced_ones():
    """72 of the stored files are fenced. A reader using json.loads would see
    about two thirds of them and say nothing about the rest."""
    recs, verdicts = _corpus()
    assert len(verdicts) > 200, (
        f"only {len(verdicts)} verdicts read; the fenced files are being "
        f"dropped somewhere")
    fams = {v["family"] for v in verdicts}
    assert fams == {"astra", "fable"}, fams


def test_the_absolutes_this_view_depends_on_agree_with_the_judged_gap():
    """The normalized gap is built from f_absolute and m_absolute, which plan
    v4 section 4 demotes in favour of the judged gap. This measures what that
    costs on this corpus."""
    _recs, verdicts = _corpus()
    worst = max(abs((v["f_absolute"] - v["m_absolute"]) - v["gap"])
                for v in verdicts if v["gap"] is not None)
    assert worst <= 0.15, worst
