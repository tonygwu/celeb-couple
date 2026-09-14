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


# -- a failed record must be counted once ------------------------------------

def test_a_fetch_failure_is_counted_as_failed_and_not_also_excluded():
    """The bug this reproduces, found from a ZERO-BYTE file.

    `data/pilot/manifests/20260914T085238Z-prose-mentions-5a9213c6.json.tmp`
    was 0 bytes. `write()` opened the temp file and then called `as_dict()`,
    which reconciles and raised, so the manifest was never written and the only
    evidence of the failure was an empty file nobody looked at.

    The cause: extract_prose_mentions.py records a fetch failure with
    `record_failure("transient_retryable")` and then sets `text = ""`, so the
    following `if not text:` ALSO fires `excluded += 1`. One attempted record,
    two buckets:

        attempted 1 but succeeded 0 + cached 0 + excluded 1 + failed 1 = 2

    The `excluded` line was added earlier to stop a genuinely empty article
    vanishing between attempted and the buckets. It was right for that case and
    wrong for this one.
    """
    s = StageSummary(stage="extract")
    s.attempted += 1
    s.record_failure("transient_retryable")
    with pytest.raises(ReconciliationError, match="double-counted"):
        s.excluded += 1
        s.reconcile()


def test_an_empty_article_that_did_not_fail_is_excluded_once():
    s = StageSummary(stage="extract")
    s.attempted += 1
    s.excluded += 1
    s.reconcile()


def test_write_leaves_no_temp_file_when_reconciliation_fails(tmp_path):
    """A zero-byte .tmp is the worst possible record of a failure: it looks
    like a stray file rather than a lost manifest."""
    from pathlib import Path
    m = RunManifest(stage_name="x", repo=Path("."), args={}, contracts={}, caps={})
    s = m.stage("broken")
    s.attempted = 1          # reconciles to 0, so as_dict() will raise
    with pytest.raises(ReconciliationError):
        m.write(tmp_path)
    assert list(tmp_path.iterdir()) == [], (
        f"left behind {[p.name for p in tmp_path.iterdir()]}"
    )


def test_an_unrecognised_error_is_not_labelled_retryable():
    """`classify_detail` returned `transient_retryable` for anything it did not
    recognise. An unknown PERMANENT error would then be retried three times,
    spend the quota, and be filed in the taxonomy under a cause it does not
    have.

    "I do not recognise this" and "this will probably work next time" are
    different statements, and only one of them is safe as a default.
    """
    from packages.llmkit.taxonomy import ALL_ERROR_TYPES, classify_detail
    assert classify_detail("something nobody has seen before") == "unclassified_failure"
    assert "unclassified_failure" in ALL_ERROR_TYPES, (
        "the manifest refuses labels outside the taxonomy, so a new label must "
        "be declared or it cannot be recorded"
    )


def test_a_recognised_error_still_classifies():
    from packages.llmkit.taxonomy import classify_detail
    assert classify_detail("auth_or_quota: hit the weekly limit") == "auth_or_quota"


def test_the_longest_matching_label_wins():
    from packages.llmkit.taxonomy import classify_detail
    assert classify_detail("cli_timeout after 600s") == "cli_timeout"


def test_an_unclassified_failure_can_be_recorded_in_a_manifest():
    """A label the manifest refuses is worse than no label: record_failure
    raises and the whole run's manifest is lost."""
    s = StageSummary(stage="x")
    s.attempted += 1
    s.record_failure("unclassified_failure")
    s.reconcile()
