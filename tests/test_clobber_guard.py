"""A smaller run must not silently replace a larger one."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from packages.llmkit.outputs import ClobberRefused, guard_output


def _write(p: Path, blob) -> None:
    p.write_text(json.dumps(blob))


def test_a_poorer_run_is_refused(tmp_path):
    out = tmp_path / "rater_noise.json"
    _write(out, {"repeats": 4})
    with pytest.raises(ClobberRefused, match="Refusing to overwrite"):
        guard_output(out, field="repeats", value=1)


def test_an_equal_or_richer_run_is_allowed(tmp_path):
    out = tmp_path / "a.json"
    _write(out, {"repeats": 4})
    guard_output(out, field="repeats", value=4)
    guard_output(out, field="repeats", value=8)


def test_force_overrides(tmp_path):
    out = tmp_path / "a.json"
    _write(out, {"repeats": 4})
    guard_output(out, field="repeats", value=1, force=True)


def test_a_missing_file_is_never_blocked(tmp_path):
    guard_output(tmp_path / "nope.json", field="repeats", value=1)


def test_a_missing_or_unreadable_field_does_not_block(tmp_path):
    out = tmp_path / "a.json"
    _write(out, {"something_else": 9})
    guard_output(out, field="repeats", value=1)
    out.write_text("not json at all")
    guard_output(out, field="repeats", value=1)


def test_unorderable_values_do_not_block(tmp_path):
    out = tmp_path / "a.json"
    _write(out, {"repeats": "four"})
    guard_output(out, field="repeats", value=1)


def test_the_message_says_how_to_proceed(tmp_path):
    out = tmp_path / "rater_noise.json"
    _write(out, {"repeats": 4})
    with pytest.raises(ClobberRefused) as exc:
        guard_output(out, field="repeats", value=1)
    text = str(exc.value)
    assert "--out" in text and "--force" in text


def test_a_dry_run_is_not_blocked_by_the_guard():
    """A dry run writes nothing, so blocking it would only teach people to reach
    for --force by reflex, which is how a guard stops guarding."""
    import subprocess
    import sys
    repo = Path(__file__).resolve().parent.parent
    artifact = repo / "data/pilot/run/rater_noise.json"
    if not artifact.exists():
        pytest.skip("no rater-noise artifact to guard")
    proc = subprocess.run(
        [sys.executable, str(repo / "scripts/measure_rater_noise.py"),
         "--judges", "fable", "--repeats", "1", "--dry-run"],
        cwd=str(repo), capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "dry run" in proc.stdout
