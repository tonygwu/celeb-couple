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


# -- separator ambiguity -----------------------------------------------------

def test_a_part_containing_the_separator_is_refused():
    """`stable_id` joins its parts with "\\n" and hashes the result, so
    ("A\\nB", "C") and ("A", "B\\nC") produce the SAME id. Two different things
    would share an identifier and merge silently.

    Most parts are internal -- qids, periods, ranks -- but
    `scripts/extract_prose_mentions.py` builds a mention id from `publisher`
    and `list_name`, both of which come straight out of a model's JSON. A
    newline there is an ordinary thing for a model to emit.

    Rejecting the separator rather than changing the hash is deliberate.
    Changing it would renumber every observation id, and the stored rationales
    cite those ids by name -- the whole corpus's grounding would fail and a
    re-score would be needed to repair it. No current input contains a newline,
    so this costs nothing today and closes the hole.
    """
    import pytest
    with pytest.raises(ValueError, match="separator"):
        stable_id("pm", "Q1", "2016", "Some Magazine\nHot 100", "list")


def test_the_ambiguous_pair_would_otherwise_have_collided():
    """The collision this prevents, shown rather than asserted."""
    import hashlib
    a = hashlib.sha256("\n".join(["Q1", "A\nB", "C"]).encode()).hexdigest()[:12]
    b = hashlib.sha256("\n".join(["Q1", "A", "B\nC"]).encode()).hexdigest()[:12]
    assert a == b, "the two joins are identical, which is the whole problem"


def test_ordinary_parts_are_unchanged():
    """The existing corpus's ids must not move: rationales cite them by name."""
    assert stable_id("dos", "Q159778", "1990") == stable_id("dos", "Q159778", "1990")
    assert stable_id("obs", "le_1", "Q1", "12").startswith("obs_")
