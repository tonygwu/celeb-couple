"""A wrong Wikidata id is the quietest error this project can make.

Everything about that person -- relationships, observations, estimates --
would be fetched correctly and be about somebody else, and nothing downstream
could tell. Nothing checked it until `scripts/verify_identities.py`.

The checker itself has one obvious way to be useless and one to be harmful.
Useless: comparing labels, which would report an error for the eleven roster
members Wikidata has no English label for. Harmful: falling back so eagerly
that it accepts a name that is genuinely wrong. Both directions are tested.

No test here touches the network.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "verify_identities", REPO / "scripts/verify_identities.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _entity(label=None, sitelink=None, instance_of="Q5"):
    e: dict = {"claims": {}}
    if label:
        e["labels"] = {"en": {"value": label}}
    if sitelink:
        e["sitelinks"] = {"enwiki": {"title": sitelink}}
    if instance_of:
        e["claims"]["P31"] = [
            {"mainsnak": {"datavalue": {"value": {"id": instance_of}}}}]
    return e


def _check(want, entity):
    return _mod().check([{"wikidata_qid": "Q1", "display_name": want}],
                        {"Q1": entity})[0]


# --------------------------------------------------------------------------
# name resolution
# --------------------------------------------------------------------------

def test_the_english_label_is_preferred():
    name, how = _mod().resolve(_entity(label="Brad Pitt", sitelink="Brad Pitt"))
    assert (name, how) == ("Brad Pitt", "label")


def test_a_person_with_no_english_label_falls_back_to_the_sitelink():
    """Eleven of the hundred roster members are in this state, including
    Denzel Washington and Zendaya. A label comparison alone would call every
    one of them an error."""
    name, how = _mod().resolve(_entity(sitelink="Zendaya"))
    assert (name, how) == ("Zendaya", "enwiki sitelink")


def test_an_entity_with_neither_resolves_to_nothing():
    """Not to the Q-id. Two partners once entered this corpus as bare ids and
    the report printed them as names."""
    name, how = _mod().resolve(_entity())
    assert name is None and how == "nothing"


def test_a_disambiguated_title_matches_the_plain_name():
    """Q178348's enwiki title is "Chris Evans (actor)" and he is Chris Evans."""
    assert _mod().strip_disambiguator("Chris Evans (actor)") == "Chris Evans"


def test_stripping_a_disambiguator_leaves_an_ordinary_name_alone():
    m = _mod()
    assert m.strip_disambiguator("Brad Pitt") == "Brad Pitt"


def test_only_a_TRAILING_parenthetical_is_stripped():
    """Otherwise a name that contains brackets would be silently truncated."""
    m = _mod()
    assert m.strip_disambiguator("A (B) C") == "A (B) C"


# --------------------------------------------------------------------------
# verdicts
# --------------------------------------------------------------------------

def test_a_matching_human_is_exact():
    assert _check("Brad Pitt", _entity(label="Brad Pitt"))["verdict"] == "exact"


def test_a_sitelink_match_is_also_exact_but_records_how():
    r = _check("Zendaya", _entity(sitelink="Zendaya"))
    assert r["verdict"] == "exact" and r["resolved_by"] == "enwiki sitelink"


def test_a_disambiguated_match_is_reported_as_such_not_hidden():
    r = _check("Chris Evans", _entity(sitelink="Chris Evans (actor)"))
    assert r["verdict"] == "exact_after_disambiguator"


def test_a_genuinely_different_person_is_a_mismatch():
    """The failure this whole script exists for."""
    r = _check("Brad Pitt", _entity(label="Bradley Cooper"))
    assert r["verdict"] == "name_mismatch"
    assert r["verdict"] in _mod().FAILING


def test_a_non_human_entity_fails():
    """A film, a category or a disambiguation page makes every fetched fact
    about it nonsense."""
    r = _check("Daredevil", _entity(label="Daredevil", instance_of="Q11424"))
    assert r["verdict"] == "not_a_human" and r["verdict"] in _mod().FAILING


def test_an_entity_with_no_name_at_all_fails():
    r = _check("Somebody", _entity())
    assert r["verdict"] == "no_english_name" and r["verdict"] in _mod().FAILING


def test_a_missing_entity_fails():
    m = _mod()
    r = m.check([{"wikidata_qid": "Q999999999", "display_name": "Nobody"}],
                {"Q999999999": {"missing": ""}})[0]
    assert r["verdict"] == "no_such_entity" and r["verdict"] in m.FAILING


def test_an_id_absent_from_the_response_is_not_silently_passed():
    """A batch that dropped a row must not read as a clean result."""
    m = _mod()
    r = m.check([{"wikidata_qid": "Q1", "display_name": "Nobody"}], {})[0]
    assert r["verdict"] in m.FAILING


# --------------------------------------------------------------------------
# the artifacts this repo currently has
# --------------------------------------------------------------------------

@pytest.mark.parametrize("rel", [
    "data/pilot/run/identity_verification.json",
    "data/roster100/run/identity_verification.json",
])
def test_every_recorded_roster_id_is_the_person_named(rel):
    import json
    path = REPO / rel
    if not path.exists():
        pytest.skip("data/ is gitignored; run scripts/verify_identities.py")
    payload = json.loads(path.read_text())
    assert payload["failures"] == [], (
        f"{rel} records roster ids that are not the person named: "
        f"{payload['failures']}")
    assert sum(payload["verdict_counts"].values()) == payload["checked"]
