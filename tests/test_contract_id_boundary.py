"""The contract id must depend on WHERE the boundary between parts falls.

The parts used to be concatenated with no separator, so moving a byte from the
end of the rubric to the start of the schema produced the same id for two
different contracts. Filed in docs/BACKLOG.md, fixed 2026-09-14 with the rubric
version bump, because fixing it changes every id.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from packages.ids.keys import CONTRACT_ID_SCHEME, contract_id  # noqa: E402


def _v1(*parts: bytes) -> str:
    """The scheme this replaced. Kept here so the test shows what it fixes."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.hexdigest()[:12]


def test_the_old_scheme_really_did_collide():
    # Not a hypothetical: this is the property the fix exists to remove.
    assert _v1(b"rubric text", b"schema text") == _v1(b"rubric tex", b"tschema text")


def test_moving_a_byte_across_the_boundary_changes_the_id():
    assert contract_id(b"rubric text", b"schema text") != contract_id(b"rubric tex", b"tschema text")


def test_an_empty_part_is_not_the_same_as_no_part():
    # Two parts, one empty, must differ from one part -- otherwise a rubric with
    # an empty schema and a schema-only contract would share an id.
    assert contract_id(b"abc", b"") != contract_id(b"abc")


def test_identical_input_is_still_stable():
    assert contract_id(b"abc", b"def") == contract_id(b"abc", b"def")


def test_the_scheme_is_named_so_a_scheme_change_is_not_read_as_a_rubric_change():
    # romance-1.0's id moved on 2026-09-14 without any rubric byte moving. A
    # reader can only tell that from the scheme tag, so it must be stamped.
    from packages.llmkit.contract import load_contract

    c = load_contract(REPO / "rubrics/romance/ROMANCE.md",
                      REPO / "rubrics/romance/romance.schema.json",
                      "romance-1.0")
    assert c.as_dict()["contract_id_scheme"] == CONTRACT_ID_SCHEME
    assert CONTRACT_ID_SCHEME == "v2-length-prefixed"
