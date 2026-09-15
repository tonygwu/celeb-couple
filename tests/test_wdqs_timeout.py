"""A 200 response can carry a truncated result set and a Java stack trace.

Measured 2026-09-15 on the real endpoint, and this is the failure shape that
looks exactly like success. The Wikidata Query Service caps a query at about
sixty seconds. It does not answer 503. It streams result rows, stops mid-JSON
when the cap hits, and appends its own log to the SAME body:

    "valSPARQL-QUERY: queryStr=
    SELECT DISTINCT ?seed ...
    java.util.concurrent.TimeoutException

The status stayed 200 and the body was 595 KB. Every liveness check passed.
`tests/fixtures/wdqs_timeout_body.txt` is the head and tail of that actual
response, kept because a hand-written imitation would only test the guess.

Nothing here touches the network.
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "tests/fixtures/wdqs_timeout_body.txt"


class _FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _serve(monkeypatch, body: str):
    from modules.records import wikidata as wd
    monkeypatch.setattr(wd.urllib.request, "urlopen",
                        lambda req, timeout=60: _FakeResponse(body.encode("utf-8")))
    return wd


def test_the_real_timed_out_body_is_diagnosed_not_just_rejected(monkeypatch):
    """The whole reason this file exists."""
    wd = _serve(monkeypatch, FIXTURE.read_text(encoding="utf-8"))
    with pytest.raises(wd.WikidataQueryTimeout) as exc:
        wd._query("SELECT 1")
    assert "split it" in str(exc.value)


def test_a_good_response_still_parses(monkeypatch):
    wd = _serve(monkeypatch, json.dumps(
        {"head": {"vars": ["x"]}, "results": {"bindings": [{"x": {"value": "1"}}]}}))
    assert wd._query("SELECT 1") == [{"x": {"value": "1"}}]


def test_a_body_broken_for_any_other_reason_is_not_relabelled(monkeypatch):
    """Relabelling every unparseable body a timeout would invent a diagnosis.

    A truncated response with no marker is still a JSONDecodeError, which is
    the honest answer when nobody knows why.
    """
    wd = _serve(monkeypatch, '{"results": {"bindings": [{"x": ')
    with pytest.raises(json.JSONDecodeError):
        wd._query("SELECT 1")


def test_a_valid_result_that_merely_quotes_the_marker_is_not_a_timeout(monkeypatch):
    """The markers are consulted only after the body fails to parse, so a row
    whose text contains one is still a row."""
    wd = _serve(monkeypatch, json.dumps({"results": {"bindings": [
        {"x": {"value": "java.util.concurrent.TimeoutException"}}]}}))
    assert wd._query("SELECT 1")[0]["x"]["value"].endswith("TimeoutException")


def test_a_timeout_is_not_retried_by_query_with_retry(monkeypatch):
    """Asking the same too-big question again wastes a minute per attempt."""
    from modules.records import wikidata as wd
    calls = {"n": 0}

    def boom(sparql, timeout=60):
        calls["n"] += 1
        raise wd.WikidataQueryTimeout("too much")

    monkeypatch.setattr(wd, "_query", boom)
    monkeypatch.setattr(wd.time, "sleep", lambda s: None)
    with pytest.raises(wd.WikidataQueryTimeout):
        wd.query_with_retry("SELECT 1")
    assert calls["n"] == 1


# --------------------------------------------------------------------------
# what the expander does about it
# --------------------------------------------------------------------------

def _expander():
    spec = importlib.util.spec_from_file_location(
        "expand_roster_timeout_test", REPO / "scripts/expand_roster.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    m.UNREACHABLE_SEEDS.clear()
    return m


def test_a_batch_that_times_out_is_halved_until_it_answers(monkeypatch):
    m = _expander()
    from modules.records import wikidata as wd
    seen: list[int] = []

    def fake(q, timeout=60):
        # Count only the seed ids. The query template names wd:Q11424 and
        # wd:Q5 of its own, and counting those made this test read 10 for a
        # chunk of 8.
        n = q.count("wd:Qz")
        seen.append(n)
        if n > 2:
            raise wd.WikidataQueryTimeout("too much")
        return [{"seed": {"value": "http://www.wikidata.org/entity/Qa"}}]

    monkeypatch.setattr(wd, "query_with_retry", fake)
    monkeypatch.setattr(wd, "PACE_SECONDS", 0)
    rows = m._fetch(m.COSTAR_QUERY, [f"Qz{i}" for i in range(8)], 40, 20000, 8, "costar")
    assert seen[0] == 8, "the first attempt uses the whole chunk"
    assert max(seen[1:]) <= 4, "it halves rather than retrying the same size"
    assert len(rows) == 4, "every surviving sub-batch's rows are kept"
    assert m.UNREACHABLE_SEEDS == []


def test_a_single_seed_that_still_times_out_is_recorded_not_dropped(monkeypatch):
    """A seed nobody could expand is a hole in the snowball, and the artifact
    has to say so. This repository already has absence_audit.py for exactly
    the difference between 'nobody looked' and 'nothing is there'."""
    m = _expander()
    from modules.records import wikidata as wd

    def always(q, timeout=60):
        if "wd:Qbad" in q:
            raise wd.WikidataQueryTimeout("too much")
        return [{"seed": {"value": "http://www.wikidata.org/entity/Qok"}}]

    monkeypatch.setattr(wd, "query_with_retry", always)
    monkeypatch.setattr(wd, "PACE_SECONDS", 0)
    rows = m._fetch(m.COSTAR_QUERY, ["Qok1", "Qbad"], 40, 20000, 2, "costar")
    assert [u["seed"] for u in m.UNREACHABLE_SEEDS] == ["Qbad"]
    assert len(rows) == 1, "the seed that DID answer is still kept"
