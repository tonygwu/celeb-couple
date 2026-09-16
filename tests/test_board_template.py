"""The board template lives IN the repo, and the page keeps the agreed shape.

It used to default to a path inside one session's scratchpad directory. That is
AGENTS.md rule 6 twice over: a checkout-absolute path that is wrong in every
other clone, and a temporary directory that disappears when the session ends.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TPL = REPO / "web/board.html"
BUILDER = REPO / "scripts/rebuild_boards.py"


def test_the_template_is_committed_in_the_repo():
    assert TPL.exists(), "web/board.html is the board template and must be tracked"


def test_the_builder_defaults_to_the_repo_template():
    src = BUILDER.read_text()
    assert 'default=str(REPO / "web/board.html")' in src


def test_no_stage_points_at_a_scratchpad_or_a_home_directory():
    for rel in ("scripts/rebuild_boards.py", "scripts/refresh_boards.sh"):
        src = (REPO / rel).read_text()
        for banned in ("/private/tmp/", "/Users/tonygwu/Code", "claude-501"):
            assert banned not in src, f"{rel} hardcodes {banned}"


def test_the_graph_flag_is_repeatable_so_real_life_boards_can_fill():
    """The IMDb graph is on-screen only. Passing it alone renders both
    real-life boards empty, which looked like a bug and was a missing input."""
    src = BUILDER.read_text()
    assert '"--graph", action="append"' in src


def test_the_refresh_passes_both_graphs():
    src = (REPO / "scripts/refresh_boards.sh").read_text()
    assert "--graph data/imdb/imdb_pairings.json" in src
    # Real life comes from relationship RECORDS, not from co-starring. See
    # tests/test_graph_domains.py.
    assert "reallife_pairings.json" in src, (
        "without a real-life graph the two real-life boards render empty")


def test_normalized_is_the_default_view():
    assert 'id="bNorm" data-basis="norm" aria-pressed="true"' in TPL.read_text()


def test_the_cumulative_rate_toggle_is_gone():
    assert "data-sort=" not in TPL.read_text()


def test_rate_is_called_average_in_the_interface():
    html = TPL.read_text()
    assert "<th>Average</th>" in html
    assert "<th>Rate</th>" not in html


def test_each_row_can_draw_a_trajectory():
    src = BUILDER.read_text()
    assert '"series"' in src, "rows must carry the person's score over time"
    assert '"year_min"' in src and '"year_max"' in src, (
        "every sparkline shares one x-axis, or the rows are not comparable")


def test_the_detail_line_is_one_line():
    """Two lines per contribution wasted vertical space; the film title moved
    onto the same line as the arithmetic."""
    html = TPL.read_text()
    assert '(${esc(c.period)}):' in html
    assert 'class="wk"' not in html
