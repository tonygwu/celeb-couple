"""The reconciliation is enforced, and a bad label cannot be invented."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.llmkit.manifest import (
    ReconciliationError, RunManifest, StageSummary, git_revision,
)

REPO = Path(__file__).resolve().parent.parent


def test_buckets_must_sum_to_attempted():
    s = StageSummary("score", attempted=10, succeeded=6, cached=1, excluded=1, failed=1)
    with pytest.raises(ReconciliationError, match="dropped or double-counted"):
        s.reconcile()
    s.failed = 2
    s.reconcile()


def test_a_failure_label_outside_the_taxonomy_is_refused():
    s = StageSummary("score")
    with pytest.raises(ValueError, match="ALL_ERROR_TYPES"):
        s.record_failure("something_went_wrong")
    s.attempted = 1
    s.record_failure("cli_timeout")
    s.reconcile()
    assert s.error_taxonomy == {"cli_timeout": 1}


def test_every_failure_lands_in_the_taxonomy_not_a_bare_count():
    s = StageSummary("score", attempted=3)
    s.record_failure("cli_timeout")
    s.record_failure("cli_timeout")
    s.record_failure("auth_or_quota")
    s.reconcile()
    assert s.failed == 3
    assert s.error_taxonomy == {"cli_timeout": 2, "auth_or_quota": 1}
    assert sum(s.error_taxonomy.values()) == s.failed


def test_a_manifest_round_trips_and_records_the_code_revision(tmp_path):
    m = RunManifest(stage_name="score", repo=REPO, args={"judges": "fable,astra"},
                    caps={"max_calls": 300})
    st = m.stage("dossiers")
    st.attempted = 2
    st.succeeded = 2
    path = m.write(tmp_path)
    blob = json.loads(path.read_text())
    assert blob["stage_name"] == "score"
    assert blob["billing"] == "subscription-only"
    assert blob["caps"]["max_calls"] == 300
    assert blob["summaries"][0]["attempted"] == 2
    assert blob["code_revision"] == git_revision(REPO)
    assert blob["run_id"].endswith(m.run_id.split("-")[-1])


def test_writing_a_manifest_with_an_unbalanced_stage_raises_rather_than_lying(tmp_path):
    m = RunManifest(stage_name="score", repo=REPO, args={})
    st = m.stage("dossiers")
    st.attempted = 5
    st.succeeded = 1
    with pytest.raises(ReconciliationError):
        m.write(tmp_path)


def test_a_halt_is_recorded_as_a_halt(tmp_path):
    m = RunManifest(stage_name="score", repo=REPO, args={})
    st = m.stage("dossiers")
    st.attempted = 1
    st.succeeded = 1
    m.halt("budget_cap_reached: 300 of 300 calls used; stopped before dos_x/astra")
    blob = json.loads(m.write(tmp_path).read_text())
    assert blob["halted"] is True
    assert "budget_cap_reached" in blob["halt_reason"]


def test_timestamps_are_utc_and_not_derived_from_the_filesystem(tmp_path):
    m = RunManifest(stage_name="score", repo=REPO, args={})
    st = m.stage("s"); st.attempted = 0
    blob = json.loads(m.write(tmp_path).read_text())
    for key in ("started_at_utc", "finished_at_utc"):
        assert blob[key].endswith("+00:00"), f"{key} must carry an explicit UTC offset"


def test_the_write_is_atomic_leaving_no_temp_file(tmp_path):
    m = RunManifest(stage_name="score", repo=REPO, args={})
    st = m.stage("s"); st.attempted = 0
    m.write(tmp_path)
    assert not list(tmp_path.glob("*.tmp"))
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_a_record_that_falls_through_every_bucket_is_caught(tmp_path):
    """The real bug this caught: a `continue` on empty input incremented
    attempted and never touched a bucket, so three of twenty-two records
    vanished silently while the run still looked clean."""
    from packages.llmkit.manifest import ReconciliationError, RunManifest
    m = RunManifest(stage_name="extract", repo=REPO, args={})
    st = m.stage("extract")
    st.attempted = 22
    st.succeeded = 19          # three records went nowhere
    with pytest.raises(ReconciliationError, match="dropped or double-counted"):
        m.write(tmp_path)
    st.excluded = 3            # now they are accounted for
    m.write(tmp_path)
