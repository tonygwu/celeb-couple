"""An artifact must not be read as current when its rubric is gone.

The grading contract is sha256(rubric + schema), so a one-line typo fix in a
rubric gives a new contract_id and every stored estimate was produced by a
rubric that no longer exists. Nothing detected that. The scores stayed on disk,
nine analysis scripts kept reading them, and every report kept presenting them
as current.

docs/BACKLOG.md has three filed rubric corrections waiting to be applied
together, so this is not hypothetical: the next person to act on any of them
would have silently invalidated the corpus while every script kept running
green.

The guard lives inside `require` rather than in each script, because
`refuse_mixed_contracts` was written as a safety function and left with no
production caller for weeks. Both directions are tested here: it must fire when
the rubric moves, and it must NOT fire on artifacts no rubric produced.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.ids.keys import contract_id
from packages.llmkit.artifacts import require
from packages.llmkit.contract import (
    StaleContractError,
    current_contract_ids,
    refuse_stale_contract,
)

REPO = Path(__file__).resolve().parent.parent


def _rubric(repo: Path, name: str, body: str = "rubric text", schema: str = "{}") -> str:
    d = repo / "rubrics" / name
    d.mkdir(parents=True)
    (d / f"{name}.md").write_text(body)
    (d / f"{name}.schema.json").write_text(schema)
    return contract_id(body.encode(), schema.encode())


# --------------------------------------------------------------------------
# current_contract_ids
# --------------------------------------------------------------------------

def test_the_ids_are_derived_from_the_directory(tmp_path):
    """Globbed, not enumerated. A fourth rubric must need no code change."""
    a = _rubric(tmp_path, "alpha", "A")
    b = _rubric(tmp_path, "beta", "B")
    assert current_contract_ids(tmp_path) == {a: "alpha", b: "beta"}


def test_the_real_repository_has_its_three_rubrics():
    ids = current_contract_ids(REPO)
    assert sorted(ids.values()) == ["mentions", "romance", "standing"]


def test_a_directory_with_two_rubric_files_is_skipped_not_guessed(tmp_path):
    """Which two files reach the judge IS the contract.

    Picking one of several candidates would compute an id for bytes nobody was
    shown, and that id would then look authoritative.
    """
    _rubric(tmp_path, "alpha", "A")
    (tmp_path / "rubrics/alpha/EXTRA.md").write_text("second")
    assert current_contract_ids(tmp_path) == {}


def test_a_directory_with_no_schema_is_skipped(tmp_path):
    _rubric(tmp_path, "alpha", "A")
    (tmp_path / "rubrics/alpha/alpha.schema.json").unlink()
    assert current_contract_ids(tmp_path) == {}


def test_a_repo_with_no_rubrics_directory_yields_nothing(tmp_path):
    assert current_contract_ids(tmp_path) == {}


# --------------------------------------------------------------------------
# refuse_stale_contract
# --------------------------------------------------------------------------

def test_a_matching_contract_passes(tmp_path):
    cid = _rubric(tmp_path, "standing", "A")
    refuse_stale_contract(tmp_path, "x.json", {"contract": {"contract_id": cid}})


def test_a_contract_no_rubric_produces_is_refused(tmp_path):
    _rubric(tmp_path, "standing", "A")
    with pytest.raises(StaleContractError) as e:
        refuse_stale_contract(tmp_path, "scores.json", {
            "contract": {"contract_id": "deadbeef0000",
                         "rubric_version": "standing-rubric-2.0"}})
    msg = str(e.value)
    assert "deadbeef0000" in msg, "the message must name the id that went stale"
    assert "scores.json" in msg, "and the artifact it came from"
    assert "CONTRACT-BUMP" in msg, "and where the procedure is written down"


def test_an_artifact_with_no_contract_block_is_not_checked(tmp_path):
    """Most artifacts are arithmetic over records. No rubric produced them."""
    _rubric(tmp_path, "standing", "A")
    refuse_stale_contract(tmp_path, "episodes.json", {"episodes": []})
    refuse_stale_contract(tmp_path, "x.json", {"contract": None})
    refuse_stale_contract(tmp_path, "x.json", {"contract": {}})


def test_an_absent_rubrics_directory_does_not_refuse(tmp_path):
    """How a fixture directory or a scratch copy passes.

    Deliberate, and the reason it is safe: production always calls this with
    the repository root, which has rubrics/. A tree without one is not this
    project.
    """
    refuse_stale_contract(tmp_path, "x.json", {"contract": {"contract_id": "zzz"}})


# --------------------------------------------------------------------------
# wired into require()
# --------------------------------------------------------------------------

def test_require_refuses_a_stale_artifact(tmp_path):
    """The nine scripts that read scored artifacts get this without knowing."""
    _rubric(tmp_path, "standing", "A")
    art = tmp_path / "data/run/scores.json"
    art.parent.mkdir(parents=True)
    art.write_text(json.dumps({"contract": {"contract_id": "deadbeef0000"}}))
    with pytest.raises(StaleContractError):
        require(tmp_path, "data/run/scores.json")


def test_require_can_be_told_to_read_a_stale_artifact_anyway(tmp_path):
    """Deciding whether to re-score means reading the thing that went stale."""
    _rubric(tmp_path, "standing", "A")
    art = tmp_path / "data/run/scores.json"
    art.parent.mkdir(parents=True)
    art.write_text(json.dumps({"contract": {"contract_id": "deadbeef0000"}}))
    got = require(tmp_path, "data/run/scores.json", check_contract=False)
    assert got["contract"]["contract_id"] == "deadbeef0000"


def test_every_scored_artifact_in_this_repo_is_current():
    """If this fails, a rubric was edited without re-scoring."""
    ids = set(current_contract_ids(REPO))
    checked = 0
    for rel in ("data/pilot/run/evidenced_scores.json",
                "data/pilot/stress/stress_report.json",
                "data/pilot/records/romance.json",
                "data/pilot/observations/prose_mentions.json",
                "data/roster100/run/joint_scores.json"):
        path = REPO / rel
        if not path.exists():
            continue
        stored = json.loads(path.read_text()).get("contract") or {}
        if not stored.get("contract_id"):
            continue
        checked += 1
        assert stored["contract_id"] in ids, (
            f"{rel} was scored under {stored['contract_id']}, which no rubric "
            "on disk produces")
    if checked == 0:
        pytest.skip("data/ is gitignored; no scored artifacts in this clone")
