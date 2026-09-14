from __future__ import annotations

import pytest

from packages.ids.keys import contract_id, json_sha256, pair_key, stable_id


def test_pair_key_is_order_independent():
    assert pair_key("p_0002", "p_0001") == pair_key("p_0001", "p_0002") == "p_0001|p_0002"


def test_pair_key_refuses_a_person_paired_with_themselves():
    with pytest.raises(ValueError):
        pair_key("p_0001", "p_0001")


def test_json_hash_ignores_key_order_but_not_content():
    assert json_sha256({"a": 1, "b": 2}) == json_sha256({"b": 2, "a": 1})
    assert json_sha256({"a": 1}) != json_sha256({"a": 2})


def test_contract_id_changes_when_any_input_byte_changes():
    base = contract_id(b"rubric", b"schema")
    assert base == contract_id(b"rubric", b"schema")
    assert base != contract_id(b"rubric ", b"schema")
    assert base != contract_id(b"rubric", b"schema ")
    # concatenation order is part of the contract
    assert base != contract_id(b"schema", b"rubric")


def test_stable_id_is_deterministic_and_prefixed():
    a = stable_id("obs", "le_1", "p_1", "rank:12")
    assert a.startswith("obs_") and a == stable_id("obs", "le_1", "p_1", "rank:12")
    assert a != stable_id("obs", "le_1", "p_1", "rank:13")
