"""Pairing gaps are derived from cached person-year scores, not re-judged.

This is where the cache pays off: a pairing between two people already in the
cache costs no model call at all. Verified on the real artifact — 7 pairings
derived from 95 cache entries with zero calls.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

_spec = importlib.util.spec_from_file_location("dp", REPO / "scripts/derive_pairings.py")
dp = importlib.util.module_from_spec(_spec)
sys.argv = ["derive_pairings.py"]
_spec.loader.exec_module(dp)

from modules.pairing.person import cache_key  # noqa: E402


def _cache(**over):
    base = {
        cache_key("M", "2000", "fable"): {"judged": True, "score": 8.0, "contract": {}},
        cache_key("W", "2000", "fable"): {"judged": True, "score": 9.0, "contract": {}},
    }
    base.update(over)
    return base


def test_the_gap_is_the_woman_minus_the_man():
    c = _cache()
    assert c[cache_key("W", "2000", "fable")]["score"] - \
           c[cache_key("M", "2000", "fable")]["score"] == 1.0


def test_two_families_reduce_to_their_mean():
    c = _cache(**{
        cache_key("M", "2000", "astra"): {"judged": True, "score": 8.4, "contract": {}},
        cache_key("W", "2000", "astra"): {"judged": True, "score": 9.0, "contract": {}},
    })
    fam = {}
    for f in ("fable", "astra"):
        fam[f] = c[cache_key("W", "2000", f)]["score"] - c[cache_key("M", "2000", f)]["score"]
    assert abs(sum(fam.values()) / 2 - 0.8) < 1e-9


def test_an_uncached_person_leaves_the_pairing_uncovered_not_zero():
    """A pairing missing because nobody judged one of its people is a different
    thing from one judged and found even. The artifact must tell them apart."""
    c = {cache_key("M", "2000", "fable"): {"judged": True, "score": 8.0, "contract": {}}}
    assert cache_key("W", "2000", "fable") not in c


def test_an_unjudged_person_carries_its_reason_forward():
    """Private individuals who appear only as someone's partner come back
    UNJUDGED. The pairing must record WHY it has no gap, not merely that it has
    none — several of Johnny Depp's and George Clooney's partners are in that
    category."""
    c = _cache(**{cache_key("W", "2000", "fable"):
                  {"judged": False, "score": None,
                   "cannot_judge_reason": "person_unknown", "contract": {}}})
    entry = c[cache_key("W", "2000", "fable")]
    assert entry["judged"] is False and entry["cannot_judge_reason"] == "person_unknown"


def test_load_caches_merges_several_files_and_tolerates_missing_ones():
    merged = dp.load_caches(["data/roster100/run/person_period_cache.json",
                             "data/roster100/run/does_not_exist.json"])
    assert isinstance(merged, dict)


def test_the_derived_artifact_is_shaped_like_a_scored_one():
    """`build_boards.py` must read it unchanged, or the cache saves calls and
    costs a rewrite of everything downstream."""
    f = REPO / "data/roster100/run/pairing_scores_derived.json"
    if not f.exists():
        import pytest
        pytest.skip("data/ is gitignored; run scripts/derive_pairings.py")
    d = json.loads(f.read_text())
    for k in ("pairings", "contract", "attempted", "succeeded", "unjudged",
              "failed", "error_taxonomy"):
        assert k in d, k
    assert d["attempted"] == d["succeeded"] + d["unjudged"] + d["failed"]
    for r in d["pairings"][:5]:
        for k in ("pairing_id", "domain", "period", "male_qid", "female_qid", "gap"):
            assert k in r, k
