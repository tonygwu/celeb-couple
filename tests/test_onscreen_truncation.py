"""A SPARQL batch that comes back at its LIMIT must raise, never be written.

Measured 2026-09-15. `fetch_onscreen_candidates.py` ran ONE query with
`LIMIT 400`. The 100-name roster produces 2570 rows, so Wikidata returned the
first 400 and dropped 2170 without saying so. The artifact recorded 136
co-starring pairs across 74 films and looked like a complete answer. The
untruncated answer is 808 pairs across 502 films.

The cost was not abstract. Gigli (Affleck + Lopez), Armageddon (Affleck +
Tyler) and Ghosted (Evans + de Armas) all have two roster members in the cast
and all three were in the discarded tail, so a reader clicking any of those
five people saw an absence that the source did not actually have.

Nothing here touches the network. `query_with_retry` is stubbed.

Set CELEB_ONSCREEN_SCRIPT to point these at another copy of the script; that is
how the pre-fix version was shown to fail.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _mod():
    path = Path(os.environ.get("CELEB_ONSCREEN_SCRIPT",
                               REPO / "scripts/fetch_onscreen_candidates.py"))
    spec = importlib.util.spec_from_file_location("onscreen_under_test", path)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _patch(monkeypatch, fake):
    """The guard lives in modules/records/wikidata.py now, so that is where
    the stub goes. Patching the script's own namespace would stub a name the
    script no longer calls and quietly test nothing."""
    from modules.records import wikidata as wdmod
    monkeypatch.setattr(wdmod, "query_with_retry", fake)
    monkeypatch.setattr(wdmod, "PACE_SECONDS", 0)


def _row(film: str, m: str, f: str) -> dict:
    return {"film": {"value": f"http://www.wikidata.org/entity/{film}"},
            "filmLabel": {"value": film},
            "m": {"value": f"http://www.wikidata.org/entity/{m}"},
            "f": {"value": f"http://www.wikidata.org/entity/{f}"}}


# --------------------------------------------------------------------------
# the guard
# --------------------------------------------------------------------------

def test_a_batch_at_its_limit_raises_instead_of_returning_short(monkeypatch):
    """The whole reason this file exists: 400 rows out of a LIMIT of 400."""
    m = _mod()
    _patch(monkeypatch, lambda q, timeout=60: [_row(f"Q{i}", "Qm", "Qf")
                                               for i in range(400)])
    with pytest.raises(m.TruncatedResult) as exc:
        m.fetch_rows(["Qm"], ["Qf"], limit=400, chunk_size=10)
    assert "400" in str(exc.value)


def test_a_batch_comfortably_under_its_limit_is_accepted(monkeypatch):
    m = _mod()
    _patch(monkeypatch, lambda q, timeout=60: [_row("Q260533", "Qm", "Qf")])
    rows, batches = m.fetch_rows(["Qm"], ["Qf"], limit=20000, chunk_size=10)
    assert len(rows) == 1 and batches == 1


def test_the_men_are_queried_in_batches_and_every_batch_is_kept(monkeypatch):
    """Batching is what makes the guard meaningful; a batch must not be lost."""
    m = _mod()
    seen: list[str] = []

    def fake(q, timeout=60):
        seen.append(q)
        return [_row(f"Qfilm{len(seen)}", "Qm", "Qf")]

    _patch(monkeypatch, fake)
    men = [f"Qm{i}" for i in range(25)]
    rows, batches = m.fetch_rows(men, ["Qf"], limit=20000, chunk_size=10)
    assert batches == 3, "25 men at 10 per batch is three batches"
    assert len(rows) == 3, "every batch's rows are kept"
    assert "wd:Qm0" in seen[0] and "wd:Qm24" in seen[2]


def test_every_woman_is_queried_in_every_batch(monkeypatch):
    """Chunking the men must not chunk the women away with them."""
    m = _mod()
    seen: list[str] = []
    _patch(monkeypatch, lambda q, timeout=60: seen.append(q) or [])
    m.fetch_rows([f"Qm{i}" for i in range(20)], ["Qf1", "Qf2"],
                 limit=20000, chunk_size=10)
    assert len(seen) == 2
    for q in seen:
        assert "wd:Qf1" in q and "wd:Qf2" in q


# --------------------------------------------------------------------------
# the query shape that made the truncation worse
# --------------------------------------------------------------------------

def test_the_query_is_distinct():
    """A film with two P31 values that both reach Q11424 yields one solution
    per path, and each duplicate counted against the LIMIT. Measured: 2570
    rows without DISTINCT, 2473 with it, same 808 pairs.
    """
    assert "SELECT DISTINCT" in _mod().QUERY


def test_the_default_row_limit_is_not_the_number_that_truncated():
    """400 was the value that silently dropped 84% of the result set."""
    defaults = {a.dest: a.default for a in _mod().build_parser()._actions}
    assert defaults["limit"] >= 20000, "the per-batch cap must clear a real batch"
    assert defaults["chunk_size"] == 10


# --------------------------------------------------------------------------
# the retry helper, which the batching made necessary
# --------------------------------------------------------------------------

def test_a_transient_502_is_retried_and_then_succeeds(monkeypatch):
    """A plain 502 on batch three crashed a fetch that had done two batches."""
    import urllib.error
    from modules.records import wikidata as wdmod
    calls = {"n": 0}

    def flaky(sparql, timeout=60):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError("u", 502, "Bad Gateway", None, None)
        return [{"ok": {"value": "1"}}]

    monkeypatch.setattr(wdmod, "_query", flaky)
    monkeypatch.setattr(wdmod.time, "sleep", lambda s: None)
    assert wdmod.query_with_retry("SELECT 1") == [{"ok": {"value": "1"}}]
    assert calls["n"] == 3


def test_a_400_is_a_bad_query_and_is_never_retried(monkeypatch):
    """Retrying a malformed query hides the error behind a delay."""
    import urllib.error
    from modules.records import wikidata as wdmod
    calls = {"n": 0}

    def bad(sparql, timeout=60):
        calls["n"] += 1
        raise urllib.error.HTTPError("u", 400, "Bad Request", None, None)

    monkeypatch.setattr(wdmod, "_query", bad)
    monkeypatch.setattr(wdmod.time, "sleep", lambda s: None)
    with pytest.raises(urllib.error.HTTPError):
        wdmod.query_with_retry("SELECT nonsense")
    assert calls["n"] == 1


def test_running_out_of_attempts_raises_rather_than_returning_nothing(monkeypatch):
    """A short result nobody can see is the defect this module was fixed for."""
    import urllib.error
    from modules.records import wikidata as wdmod
    monkeypatch.setattr(wdmod, "_query", lambda s, timeout=60: (_ for _ in ()).throw(
        urllib.error.HTTPError("u", 503, "Service Unavailable", None, None)))
    monkeypatch.setattr(wdmod.time, "sleep", lambda s: None)
    with pytest.raises(urllib.error.HTTPError):
        wdmod.query_with_retry("SELECT 1", attempts=2)
