"""A backgrounded run must show progress, or a working run looks hung.

The first 300-film batch wrote an empty log for several minutes because Python
buffers stdout when it is not a terminal. The run was fine. There was no way to
see that from outside, which is the same failure mode as a bare completion
count: a healthy component and a dead one look identical.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
LONG_RUNNING = ("identify_couples.py", "score_person_periods.py")


@pytest.mark.parametrize("name", LONG_RUNNING)
def test_per_item_progress_lines_flush(name):
    path = REPO / "scripts" / name
    assert path.exists(), f"{name} was renamed; this guard now checks nothing"
    lines = path.read_text().splitlines()
    progress = [l for l in lines if "[{i}/" in l or "[{n}/" in l]
    assert progress, f"{name} prints no per-item progress line at all"
    body = "\n".join(lines)
    for frag in ("[{i}/", "[{n}/"):
        if frag not in body:
            continue
        idx = body.index(frag)
        stmt = body[body.rindex("print(", 0, idx): body.index(")\n", idx) + 1]
        assert "flush=True" in stmt, (
            f"{name}'s progress line does not flush, so a backgrounded run "
            "shows an empty log and looks hung")
