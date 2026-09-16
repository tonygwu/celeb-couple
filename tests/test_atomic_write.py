"""A cache written while the boards are refreshing must never be read half-way.

`Path.write_text` truncates and then writes. Two scoring runs now append to
their caches WHILE the refresh chain reads them, so a reader could open a
truncated JSON document. The scoring runs are hours long; losing one to a
refresh is not acceptable, and neither is a board built from half a cache.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.llmkit.atomic import write_json_atomic

WRITERS = ("scripts/score_person_periods.py", "scripts/identify_couples.py")
REPO = Path(__file__).resolve().parent.parent


def test_it_writes_readable_json(tmp_path):
    dest = tmp_path / "c.json"
    write_json_atomic(dest, {"a": 1}, indent=1)
    assert json.loads(dest.read_text()) == {"a": 1}


def test_it_leaves_no_temporary_file_behind(tmp_path):
    dest = tmp_path / "c.json"
    write_json_atomic(dest, {"a": 1})
    assert [p.name for p in tmp_path.iterdir()] == ["c.json"]


def test_a_failed_write_leaves_the_previous_file_intact(tmp_path):
    """The whole point: a reader sees the WHOLE old file or the whole new one."""
    dest = tmp_path / "c.json"
    write_json_atomic(dest, {"good": True})

    class Unserializable:
        pass

    with pytest.raises(TypeError):
        write_json_atomic(dest, {"bad": Unserializable()})
    assert json.loads(dest.read_text()) == {"good": True}
    assert [p.name for p in tmp_path.iterdir()] == ["c.json"], "temp file left behind"


def test_it_creates_the_parent_directory(tmp_path):
    dest = tmp_path / "deep" / "er" / "c.json"
    write_json_atomic(dest, [1, 2])
    assert json.loads(dest.read_text()) == [1, 2]


@pytest.mark.parametrize("rel", WRITERS)
def test_the_long_running_writers_use_the_atomic_write(rel):
    src = (REPO / rel).read_text()
    assert "write_json_atomic(cache_path" in src, (
        f"{rel} writes its cache non-atomically, so the refresh chain can read "
        "a truncated file")
    assert "cache_path.write_text(" not in src
