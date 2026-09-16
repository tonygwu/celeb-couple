"""Only romance-checked pairings reach the board.

The Wikidata graph comes from fetch_onscreen_candidates.py, which finds films
where a male and a female roster member CO-STAR. Co-starring is not a romance.
Its `centrality` field is the romance check, and 21 of its 75 on-screen pairs
never got one: Exit Through the Gift Shop (a Banksy documentary), the SNL 50th
Anniversary Special, and The Batman: Part II, which is dated 2028 and does not
exist yet.

Merging that graph whole to recover its real-life pairings put all of it on the
board, which is how Idris Elba was shown paired with Scarlett Johansson in
Avengers: Age of Ultron, where he is Heimdall and she is Black Widow, and in
The Jungle Book, where he is a tiger and she is a snake.

The IMDb pipeline covers on-screen and IS romance-checked, by
scripts/identify_couples.py. So only `real_life` is taken from the other graph.
"""
from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REFRESH = (REPO / "scripts/refresh_boards.sh").read_text()
BUILDER = (REPO / "scripts/rebuild_boards.py").read_text()


def test_the_graph_flag_supports_a_domain_suffix():
    assert 'rel, _, only = spec.partition("#")' in BUILDER


def test_the_refresh_takes_only_real_life_from_the_unchecked_graph():
    assert "pairing_scores.json#real_life" in REFRESH, (
        "taking that graph whole puts un-romance-checked co-star pairs on the "
        "board -- Idris Elba and Scarlett Johansson in The Jungle Book")


def test_the_refresh_does_not_take_that_graph_whole():
    for line in REFRESH.splitlines():
        s = line.strip()
        if s.startswith("--graph") and "pairing_scores.json" in s:
            assert "#real_life" in s, f"unfiltered: {s}"


def test_the_reason_is_recorded_where_someone_would_change_it():
    """A future agent adding on-screen coverage will look right here."""
    assert "no romance check" in REFRESH
    assert "Jungle Book" in REFRESH or "Age of Ultron" in REFRESH


def test_the_imdb_graph_is_still_passed_whole():
    """It is romance-checked, so it needs no filter."""
    assert "--graph data/imdb/imdb_pairings.json" in REFRESH
