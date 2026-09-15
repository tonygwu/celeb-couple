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


def test_the_real_repository_has_its_rubrics():
    """Every rubric directory on disk produces exactly one contract id.

    This pinned the list to three names and broke when `pairing` was added for
    plan v4 -- a hardcoded set going stale after the set grew, for the third
    time in this repo. Derived from the directory listing now, so a fifth rubric
    needs no edit here.
    """
    ids = current_contract_ids(REPO)
    on_disk = sorted(d.name for d in (REPO / "rubrics").iterdir()
                     if d.is_dir() and len(list(d.glob("*.md"))) == 1
                     and len(list(d.glob("*.schema.json"))) == 1)
    assert sorted(ids.values()) == on_disk
    assert len(ids) == len(on_disk), "two rubrics produced the same contract id"


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
    """If this fails, a rubric was edited without re-scoring.

    GLOBBED, not listed. The list this replaced named five artifacts and missed
    `data/pilot/run/pilot_report.json` and `data/pilot/run/rater_noise.json`,
    both of which carry a contract block. The 2026-09-14 bump found them with a
    shell preflight that globbed, which is the second time in this repo a
    hardcoded set of paths went stale after the set grew.

    `history/` is excluded on purpose: an archived artifact is SUPPOSED to
    record the contract it was scored under, and that contract is expected to be
    gone. Refusing it would make keeping history impossible.
    """
    stale, checked = [], 0
    for path in sorted((REPO / "data").glob("**/*.json")):
        if "history" in path.parts:
            continue
        try:
            data = json.loads(path.read_text()) or {}
        except (ValueError, OSError):
            continue
        stored = data.get("contract")
        if not isinstance(stored, dict) or not stored.get("contract_id"):
            continue
        checked += 1
        # Calls the REAL guard rather than reimplementing its rule. The
        # reimplementation drifted the moment the guard gained its zero-call
        # exemption: this test kept failing on an artifact production correctly
        # allows. A test that copies the logic it checks tests the copy.
        try:
            refuse_stale_contract(REPO, str(path.relative_to(REPO)), data)
        except SystemExit:
            stale.append(f"{path.relative_to(REPO)} ({stored['contract_id']}, "
                         f"{stored.get('rubric_version', '?')})")
    if checked == 0:
        pytest.skip("data/ is gitignored; no scored artifacts in this clone")
    assert not stale, (
        "these artifacts were scored under a contract no rubric on disk "
        "produces:\n  " + "\n  ".join(stale)
        + "\nRe-score before reporting. See docs/CONTRACT-BUMP.md.")


def test_the_scored_artifacts_carry_a_contract_block_at_all():
    """A missing block makes BOTH provenance guards silent no-ops.

    `refuse_stale_contract` returns early when there is no block, and
    `refuse_mixed_contracts` keys on a per-record id that this pipeline never
    writes. `person_period_scores.json` carried 39 estimates and no block, so
    neither guard could say anything about it.
    """
    must_carry = ("data/pilot/run/evidenced_scores.json",
                  "data/pilot/run/person_period_scores.json")
    present = [rel for rel in must_carry if (REPO / rel).exists()]
    if not present:
        pytest.skip("data/ is gitignored; no scored artifacts in this clone")
    missing = [rel for rel in present
               if not ((json.loads((REPO / rel).read_text()) or {})
                       .get("contract") or {}).get("contract_id")]
    assert not missing, (
        f"scored artifacts with no contract block: {missing}. Both provenance "
        "guards are no-ops on a file without one.")


def test_an_artifact_whose_run_called_no_judge_is_not_refused():
    """A zero-call run has no estimate for a rubric to have produced.

    `data/pilot/run/pilot_report.json` records sent_to_judges 0, scored 0, and
    calls_made 0 on both judges: every dossier was empty and short-circuited
    before any judge ran. It still carries a contract block, because the script
    stamps which bytes WOULD have been sent, so after the 2026-09-15 rubric bump
    it read as stale and blocked the whole report pass.

    Refusing it is a false positive. The guard already skips an artifact with no
    contract block at all, for exactly this reason; this one happens to have one.
    """
    data = {"contract": {"contract_id": "gone-forever", "rubric_version": "x"},
            "budgets": {"fable": {"calls_made": 0}, "astra": {"calls_made": 0}}}
    refuse_stale_contract(REPO, "zero_call.json", data)     # must not raise


def test_a_stale_artifact_that_DID_call_a_judge_is_still_refused():
    """The exemption must be narrow. One call made is one estimate that came
    from a rubric, and a rubric that is gone cannot be read as current."""
    data = {"contract": {"contract_id": "gone-forever", "rubric_version": "x"},
            "budgets": {"fable": {"calls_made": 1}, "astra": {"calls_made": 0}}}
    with pytest.raises(SystemExit):
        refuse_stale_contract(REPO, "one_call.json", data)


def test_an_empty_budgets_block_does_not_buy_an_exemption():
    """`budgets: {}` says nothing about whether a judge ran. `all()` over an
    empty dict is True, which would have silently exempted every artifact
    carrying an empty budgets block."""
    data = {"contract": {"contract_id": "gone-forever", "rubric_version": "x"},
            "budgets": {}}
    with pytest.raises(SystemExit):
        refuse_stale_contract(REPO, "empty_budgets.json", data)
