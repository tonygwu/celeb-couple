"""Merging the same mentions twice must add nothing the second time.

Demonstrated empirically across clones on 2026-09-14: repo-0's observation file
records three merge passes, the last of which added 0 observations and found 10
duplicates. That is the dedup key doing its job, and it is worth pinning,
because a merge that is not idempotent silently inflates independence every
time someone re-runs the chain.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _write(path: Path, blob) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(blob, indent=2))


def test_merging_the_same_mentions_twice_adds_nothing_the_second_time(tmp_path):
    obs = {
        "generated_at_utc": "2026-09-14T00:00:00Z",
        "editions": [{
            "list_edition_id": "le_1", "publisher": "PEOPLE",
            "title": "Sexiest Man Alive 2002", "published_at": "2002",
            "published_precision": "year", "concerns_period": "2002",
            "candidate_set_described": "men in entertainment", "list_length": 1,
            "content_sha256": "0" * 64,
        }],
        "observations": [{
            "observation_id": "obs_1", "person_id": "Q1", "list_edition_id": "le_1",
            "evidence_type": "editorial_award",
            "observed": {"award_name": "Sexiest Man Alive", "winner": True},
            "concerns_period": "2002", "published_at": "2002",
            "excerpt": "named winner", "excerpt_locator": "table",
            "lineage": {"original_source": "le_1", "is_syndicated_copy": False},
            "review_status": "pending",
        }],
    }
    mentions = {"mentions": [
        # the SAME judgment reached via prose, and a genuinely new one
        {"person_id": "Q1", "person": "A", "year": 2002, "publisher": "People",
         "list_name": "Sexiest Man Alive", "shape": "editorial_award",
         "rank": None, "list_length": None, "evidence": "named Sexiest Man Alive",
         "article_sha256": "a" * 64, "mention_id": "pm_1"},
        {"person_id": "Q1", "person": "A", "year": 2004, "publisher": "Empire",
         "list_name": "25 sexiest stars", "shape": "unordered_inclusion",
         "rank": None, "list_length": 25, "evidence": "one of the 25 sexiest",
         "article_sha256": "a" * 64, "mention_id": "pm_2"},
    ]}

    obs_path = tmp_path / "observations.json"
    men_path = tmp_path / "mentions.json"
    _write(obs_path, obs)
    _write(men_path, mentions)

    def run():
        return subprocess.run(
            [sys.executable, str(REPO / "scripts/merge_prose_mentions.py"),
             "--observations", str(obs_path),
             "--mentions", str(men_path), "--out", str(obs_path)],
            capture_output=True, text=True, cwd=str(REPO), timeout=60)

    first = run()
    assert first.returncode == 0, first.stderr
    after_one = json.loads(obs_path.read_text())
    # the prose copy of the award dedups against the table row; Empire is new
    assert len(after_one["observations"]) == 2

    second = run()
    assert second.returncode == 0, second.stderr
    after_two = json.loads(obs_path.read_text())
    assert len(after_two["observations"]) == 2, (
        "re-running the merge must add nothing; a non-idempotent merge inflates "
        "independence every time the chain is re-run"
    )
    assert after_two["merges"][-1]["added"] == 0
    assert after_two["coverage"]["total_observations"] == 2
