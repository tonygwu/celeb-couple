"""The snowball's bounds and its ranking, neither of which may drift silently.

The roster is a closed 100-person set, so a reader could click Adam Sandler and
find 50 First Dates missing purely because Drew Barrymore is not on it. The
expansion fixes that, and every bound it applies is a judgment call that has to
stay readable: which candidates outrank which, how the per-round cap is split
between the sexes, and when the snowball stops.

Nothing here touches the network.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "expand_roster_under_test", REPO / "scripts/expand_roster.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _rec(qid, sex="male", sitelinks=50, edges=("onscreen_costar",), seeds=("Qs",)):
    return {"wikidata_qid": qid, "display_name": qid, "gender_category": sex,
            "sitelinks": sitelinks, "edges": set(edges), "seeds": set(seeds)}


def _row(seed, other, label, gender_qid, sitelinks):
    e = "http://www.wikidata.org/entity/"
    return {"seed": {"value": e + seed}, "other": {"value": e + other},
            "otherLabel": {"value": label}, "g": {"value": e + gender_qid},
            "sl": {"value": str(sitelinks)}}


MALE, FEMALE, NONBINARY = "Q6581097", "Q6581072", "Q48270"


# --------------------------------------------------------------------------
# collect
# --------------------------------------------------------------------------

def test_somebody_already_on_the_roster_is_not_a_candidate():
    m = _mod()
    rows = [_row("Qs1", "Qold", "Already Here", MALE, 90)]
    assert m.collect(rows, "onscreen_costar", {"Qold"}) == {}


def test_a_gender_wikidata_does_not_record_as_male_or_female_is_left_out():
    """The pairing product needs one of each. An unmapped value is never
    guessed into a bucket, which is the rule fetch_gender already follows."""
    m = _mod()
    rows = [_row("Qs1", "Qnb", "Nonbinary Person", NONBINARY, 200)]
    assert m.collect(rows, "onscreen_costar", set()) == {}


def test_reach_counts_distinct_seeds_not_rows():
    """Two films with the same seed is one seed, not two."""
    m = _mod()
    rows = [_row("Qs1", "Qx", "X", MALE, 50), _row("Qs1", "Qx", "X", MALE, 50),
            _row("Qs2", "Qx", "X", MALE, 50)]
    got = m.collect(rows, "onscreen_costar", set())
    assert got["Qx"]["seeds"] == {"Qs1", "Qs2"}


def test_both_edge_types_survive_a_merge():
    m = _mod()
    a = m.collect([_row("Qs1", "Qx", "X", MALE, 50)], "real_life_partner", set())
    b = m.collect([_row("Qs2", "Qx", "X", MALE, 50)], "onscreen_costar", set())
    got = m.merge(a, b)
    assert got["Qx"]["edges"] == {"real_life_partner", "onscreen_costar"}
    assert got["Qx"]["seeds"] == {"Qs1", "Qs2"}


# --------------------------------------------------------------------------
# rank_key
# --------------------------------------------------------------------------

def test_a_real_life_partner_outranks_a_better_connected_costar():
    """The operator asked for people who "also dated in real life". Wikidata
    can source that half and cannot source the romance half for free."""
    m = _mod()
    partner = _rec("Q1", edges=("real_life_partner",), seeds=("Qa",), sitelinks=30)
    costar = _rec("Q2", edges=("onscreen_costar",),
                  seeds=("Qa", "Qb", "Qc"), sitelinks=300)
    assert m.rank_key(partner) > m.rank_key(costar)


def test_among_costars_more_roster_reach_wins_over_prominence():
    m = _mod()
    wide = _rec("Q1", seeds=("Qa", "Qb", "Qc"), sitelinks=45)
    famous = _rec("Q2", seeds=("Qa",), sitelinks=300)
    assert m.rank_key(wide) > m.rank_key(famous)


def test_a_tie_is_broken_by_qid_so_the_order_never_depends_on_iteration():
    m = _mod()
    a, b = _rec("Q100", seeds=("Qa",)), _rec("Q200", seeds=("Qa",))
    assert m.rank_key(a) != m.rank_key(b)
    taken, _ = m.admit({"Q100": a, "Q200": b}, cap=1, balance=False, headroom=99)
    assert taken[0]["wikidata_qid"] == "Q100", "lower Q-id wins a dead tie"


# --------------------------------------------------------------------------
# admit: the bounds
# --------------------------------------------------------------------------

def test_the_per_round_cap_holds_and_reports_what_it_cut():
    m = _mod()
    cands = {f"Q{i}": _rec(f"Q{i}", seeds=("Qa",)) for i in range(1, 21)}
    taken, cut = m.admit(cands, cap=5, balance=False, headroom=99)
    assert len(taken) == 5 and cut == 15


def test_headroom_beats_the_cap_so_max_people_cannot_be_exceeded():
    m = _mod()
    cands = {f"Q{i}": _rec(f"Q{i}") for i in range(1, 21)}
    taken, cut = m.admit(cands, cap=60, balance=False, headroom=3)
    assert len(taken) == 3 and cut == 17


def test_balancing_splits_the_cap_evenly_between_the_sexes():
    """The seed roster is deliberately 50/50 and an unbalanced snowball would
    quietly undo that, because a male-led film's cast is not evenly split."""
    m = _mod()
    cands = {f"Qm{i}": _rec(f"Q{100 + i}", "male", seeds=("Qa", "Qb"))
             for i in range(20)}
    cands.update({f"Qf{i}": _rec(f"Q{200 + i}", "female", seeds=("Qa",))
                  for i in range(20)})
    taken, _ = m.admit(cands, cap=10, balance=True, headroom=99)
    assert sum(1 for r in taken if r["gender_category"] == "male") == 5
    assert sum(1 for r in taken if r["gender_category"] == "female") == 5


def test_a_sex_with_too_few_candidates_leaves_room_the_other_fills():
    """Refusing to fill the empty half would cut people for no reason."""
    m = _mod()
    cands = {f"Qm{i}": _rec(f"Q{100 + i}", "male") for i in range(20)}
    cands["Qf0"] = _rec("Q900", "female")
    taken, _ = m.admit(cands, cap=10, balance=True, headroom=99)
    assert len(taken) == 10
    assert sum(1 for r in taken if r["gender_category"] == "female") == 1


def test_no_candidates_admits_nobody_rather_than_erroring():
    m = _mod()
    assert m.admit({}, cap=60, balance=True, headroom=99) == ([], 0)


# --------------------------------------------------------------------------
# the truncation guard, same defect as the on-screen fetcher
# --------------------------------------------------------------------------

def test_a_batch_at_its_row_limit_raises(monkeypatch):
    import pytest
    m = _mod()
    from modules.records import wikidata as wdmod
    monkeypatch.setattr(wdmod, "query_with_retry", lambda q, timeout=60: [{}] * 50)
    monkeypatch.setattr(wdmod, "PACE_SECONDS", 0)
    with pytest.raises(m.TruncatedResult):
        m._fetch(m.COSTAR_QUERY, ["Qa"], 40, 50, 5, "costar")


# --------------------------------------------------------------------------
# the defaults, which are the recorded stopping rule
# --------------------------------------------------------------------------

def test_every_bound_is_an_argument_with_a_recorded_default():
    """A cap chosen inside the code is an unreviewed judgment call."""
    d = {a.dest: a.default for a in _mod().build_parser()._actions}
    for name in ("rounds", "converge_at", "per_round_cap", "max_people",
                 "min_sitelinks", "partner_min_sitelinks", "balance", "edges"):
        assert name in d, f"{name} must be an argument, not a buried constant"
        assert d[name] is not None, f"{name} has no recorded default"
    assert d["rounds"] >= 1
    assert d["max_people"] >= d["per_round_cap"]
    assert d["partner_min_sitelinks"] <= d["min_sitelinks"]


# --------------------------------------------------------------------------
# names: a roster row reading "Q2023710" names nobody
# --------------------------------------------------------------------------

def test_a_bare_qid_name_is_resolved_through_the_enwiki_sitelink(monkeypatch):
    """Eleven of the original hundred have no English Wikidata label at all.
    Two pilot partners and ten roster partners once entered the corpus as bare
    ids for exactly this reason and their episodes were excluded as defective.
    """
    m = _mod()
    monkeypatch.setattr(m, "fetch_labels",
                        lambda qids: {"Q2023710": "Tom Holland"})
    roster = [{"display_name": "Q2023710", "wikidata_qid": "Q2023710"},
              {"display_name": "Mel Gibson", "wikidata_qid": "Q42229"}]
    resolved, unresolved = m.resolve_bare_qids(roster)
    assert roster[0]["display_name"] == "Tom Holland"
    assert roster[1]["display_name"] == "Mel Gibson", "a real name is untouched"
    assert resolved == ["Q2023710"] and unresolved == []


def test_somebody_with_no_label_and_no_article_is_reported_not_hidden(monkeypatch):
    m = _mod()
    monkeypatch.setattr(m, "fetch_labels", lambda qids: {})
    roster = [{"display_name": "Q99999999", "wikidata_qid": "Q99999999"}]
    resolved, unresolved = m.resolve_bare_qids(roster)
    assert resolved == [] and unresolved == ["Q99999999"]
    assert roster[0]["display_name"] == "Q99999999", "never guessed at"


def test_no_lookup_happens_when_every_name_is_real(monkeypatch):
    m = _mod()
    called = {"n": 0}

    def counted(qids):
        called["n"] += 1
        return {}

    monkeypatch.setattr(m, "fetch_labels", counted)
    assert m.resolve_bare_qids(
        [{"display_name": "Mel Gibson", "wikidata_qid": "Q42229"}]) == ([], [])
    assert called["n"] == 0


# --------------------------------------------------------------------------
# --must-include: a bounded snowball cannot promise a specific person
# --------------------------------------------------------------------------

def test_a_named_person_joins_as_a_seed_with_sourced_name_and_gender(monkeypatch):
    """Minnie Driver is the worked example. She is rank 455 among round-1
    women, so a balanced per-round cap would have to be at least 910 -- a
    roster of 1010 after one round -- for the snowball to reach her."""
    m = _mod()
    monkeypatch.setattr(m, "fetch_gender", lambda q: {"Q229056": "female"})
    monkeypatch.setattr(m, "fetch_labels", lambda q: {"Q229056": "Minnie Driver"})
    people, refused = m.seed_named(["Q229056"], set())
    assert refused == []
    assert people[0]["display_name"] == "Minnie Driver"
    assert people[0]["gender_category"] == "female"
    assert people[0]["named_explicitly"] is True, (
        "a named person must not read as something the snowball found")


def test_somebody_already_on_the_roster_is_not_added_twice(monkeypatch):
    m = _mod()
    monkeypatch.setattr(m, "fetch_gender", lambda q: {})
    monkeypatch.setattr(m, "fetch_labels", lambda q: {})
    assert m.seed_named(["Q42229"], {"Q42229"}) == ([], [])


def test_a_gender_wikidata_does_not_record_is_refused_with_a_reason(monkeypatch):
    """The caller never supplies gender. The pairing product needs one of
    each, and a person Wikidata does not record is refused, not guessed."""
    m = _mod()
    monkeypatch.setattr(m, "fetch_gender", lambda q: {})
    monkeypatch.setattr(m, "fetch_labels", lambda q: {"Q1": "Someone"})
    people, refused = m.seed_named(["Q1"], set())
    assert people == []
    assert refused and "unrecorded" in refused[0]


def test_a_person_with_no_english_name_at_all_is_refused(monkeypatch):
    m = _mod()
    monkeypatch.setattr(m, "fetch_gender", lambda q: {"Q1": "female"})
    monkeypatch.setattr(m, "fetch_labels", lambda q: {})
    people, refused = m.seed_named(["Q1"], set())
    assert people == [] and "no English label" in refused[0]
