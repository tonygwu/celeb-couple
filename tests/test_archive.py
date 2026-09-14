"""Score artifacts must be archived before they are overwritten.

Re-scoring the pilot corpus replaced every estimate in place. The previous
run's numbers were simply gone, which is why tonight's run-to-run stability
measurement rests on three rows: the pilot and the roster corpora happened to
overlap on three person-periods, so the comparison was available by accident.

Run-to-run variance turned out to be a headline finding -- two of those three
estimates moved by 2.0 points on byte-identical dossiers -- and it should be
measurable on the whole corpus rather than on an accident.

`guard_output` already refuses to replace a RICHER artifact with a poorer one.
It says nothing about an equally rich replacement, which is the normal case
here and the one that loses the history.
"""
from __future__ import annotations

import json

from packages.llmkit.outputs import archive_previous


def test_the_previous_contents_are_kept(tmp_path):
    p = tmp_path / "scores.json"
    p.write_text(json.dumps({"n": 1}))
    kept = archive_previous(p)
    assert kept is not None and kept.exists()
    assert json.loads(kept.read_text()) == {"n": 1}


def test_archiving_does_not_remove_the_original(tmp_path):
    """It runs BEFORE the new write, so deleting here would lose the artifact
    entirely if the write then failed."""
    p = tmp_path / "scores.json"
    p.write_text(json.dumps({"n": 1}))
    archive_previous(p)
    assert p.exists() and json.loads(p.read_text()) == {"n": 1}


def test_a_missing_file_archives_nothing_and_does_not_raise(tmp_path):
    assert archive_previous(tmp_path / "absent.json") is None


def test_identical_contents_do_not_pile_up(tmp_path):
    """Content-addressed: re-running with no change must not grow the history,
    or a nightly chain would fill the disk with copies of one answer."""
    p = tmp_path / "scores.json"
    p.write_text(json.dumps({"n": 1}))
    first = archive_previous(p)
    second = archive_previous(p)
    assert first == second
    assert len(list(first.parent.iterdir())) == 1


def test_different_contents_are_kept_separately(tmp_path):
    p = tmp_path / "scores.json"
    p.write_text(json.dumps({"n": 1}))
    a = archive_previous(p)
    p.write_text(json.dumps({"n": 2}))
    b = archive_previous(p)
    assert a != b
    assert len(list(a.parent.iterdir())) == 2
    assert {json.loads(f.read_text())["n"] for f in a.parent.iterdir()} == {1, 2}


def test_the_archive_sits_beside_the_artifact_not_inside_the_repo(tmp_path):
    p = tmp_path / "run" / "scores.json"
    p.parent.mkdir()
    p.write_text("{}")
    kept = archive_previous(p)
    assert kept.parent == p.parent / "history"
    assert kept.name.startswith("scores-")
