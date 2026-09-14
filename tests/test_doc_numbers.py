"""The doc-number cross-check must find a stale number wherever it is written.

`tests/test_doc_claims.py` guards two quantities in README.md by name. It
caught three stale numbers in one night and is worth keeping. What it could not
do is look anywhere else: the same 42% sat wrong in `docs/BACKLOG.md` and
`docs/BACKLOG-roster.md` the whole time, because nothing checked those files.

`scripts/audit_doc_numbers.py` checks every tracked Markdown file against the
artifacts. These tests cover the part that can go quietly wrong -- the matching
-- rather than the artifact reading, because a guard that silently matches
nothing reports a clean audit forever.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "audit_doc_numbers", REPO / "scripts/audit_doc_numbers.py")
    m = importlib.util.module_from_spec(spec)
    # Register before exec: @dataclass resolves its string annotations through
    # sys.modules[cls.__module__], and raises KeyError if the module is not
    # there yet. The script itself is unaffected -- it runs as __main__.
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _rule(mod, name):
    for r in mod.RULES:
        if r.name == name:
            return r
    raise AssertionError(f"no rule named {name}")


def test_a_stale_number_is_found():
    mod = _mod()
    hits = mod.find_mismatches(
        _rule(mod, "shape_confound_pct"), "39",
        {"docs/X.md": "Evidence type alone explains 42% of the estimate."})
    assert len(hits) == 1
    assert hits[0]["written"] == "42" and hits[0]["artifact_says"] == "39"


def test_a_current_number_is_not_reported():
    mod = _mod()
    assert mod.find_mismatches(
        _rule(mod, "shape_confound_pct"), "39",
        {"docs/X.md": "shape explains 39% of the estimate"}) == []


def test_a_number_wrapped_across_a_line_is_still_found():
    """The first version of this script missed exactly this, and reported the
    file clean. Prose wraps wherever the author's editor wrapped it."""
    mod = _mod()
    hits = mod.find_mismatches(
        _rule(mod, "shape_confound_pct"), "39",
        {"docs/X.md": "Evidence type alone explains 42% of the\n  estimate."})
    assert len(hits) == 1, "a line wrap must not hide a stale number"


def test_the_reported_line_number_points_at_the_stale_line():
    mod = _mod()
    hits = mod.find_mismatches(
        _rule(mod, "shape_confound_pct"), "39",
        {"docs/X.md": "one\ntwo\nthree\nshape explains 42% of the estimate\n"})
    assert hits[0]["line"] == 4


def test_a_skipped_document_is_not_checked():
    """The roster corpus has different denominators. A pilot rule firing there
    would be a false alarm, and one false alarm teaches the next agent to
    ignore the whole script."""
    mod = _mod()
    rule = _rule(mod, "total_observations")
    doc = {"docs/SCALING.md": "131 observations over 49 of 100 people"}
    assert "docs/SCALING.md" in rule.skip
    assert mod.find_mismatches(rule, "41", doc) == []


def test_every_rule_matches_the_text_it_claims_to_match():
    """A rule whose pattern matches nothing reports a clean audit forever.

    This is the failure mode that makes a guard worse than no guard, so each
    rule carries a sample of the phrasing it exists to police and must find it.
    """
    mod = _mod()
    samples = {
        "shape_confound_pct": "shape explains 99% of the estimate",
        "total_observations": "yielded 99 observations over 9 of 14 people",
        "gender_offset": "the male mean sits 99.9 points above the female mean",
        "female_ranked_observations": "Women hold 99 ranked observations",
        "real_distinct_values": "It now produces 99 across a range of 30.0",
        "ranked_lsd": "against an LSD of 99.9",
        "roster_observations": "Corpus: 99 observations over 49 of 100 roster people",
        "roster_people_with_evidence": "131 observations over 99 of 100 roster people",
        "scorable_episodes": "and 99 scorable relationship episodes",
        "coverage_saturation": "is about 99 of 239 episodes",
    }
    assert set(samples) == {r.name for r in mod.RULES}, (
        "a new rule was added without a sample proving its pattern matches"
    )
    for rule in mod.RULES:
        hits = mod.find_mismatches(rule, "0", {"docs/sample.md": samples[rule.name]})
        assert len(hits) == 1, f"{rule.name} does not match its own sample phrasing"


def test_generated_documents_are_not_audited():
    """Hand-editing a generated file is the bug; re-running the generator is
    the fix. Reporting it here would send the reader to the wrong place."""
    mod = _mod()
    assert "docs/M0-REPORT.md" in mod.GENERATED


def test_the_repository_currently_passes_the_audit():
    """Optional: needs the artifacts, which live under a gitignored data/."""
    if not (REPO / "data/pilot/run/shape_confound.json").exists():
        pytest.skip("data/ is gitignored; nothing to audit in a fresh clone")
    r = subprocess.run([str(REPO / ".venv/bin/python"),
                        str(REPO / "scripts/audit_doc_numbers.py")],
                       capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, f"stale numbers in the docs:\n{r.stdout}"


def test_a_number_at_the_end_of_a_sentence_is_captured_without_the_period():
    """`[\\d.]+` is greedy: "LSD of 2.4." captured "2.4." and never equalled the
    artifact's "2.4", so a correct document was reported stale. A guard that
    reports false positives is worse than no guard."""
    mod = _mod()
    assert mod.find_mismatches(
        _rule(mod, "ranked_lsd"), "2.4",
        {"docs/X.md": "The one comparable gap is 0.0 against an LSD of 2.4."}) == []


def test_the_historical_pooled_figure_is_not_reported_as_stale():
    """docs/THE-TRAP.md deliberately quotes the old pooled LSD to explain why
    it was wrong. A looser pattern would flag that correct sentence."""
    mod = _mod()
    historical = ("It also means the published least significant difference of\n"
                  "1.2 points was too small: it pooled the award dossier's zero "
                  "measured variance with the ranked dossier's.")
    assert mod.find_mismatches(
        _rule(mod, "ranked_lsd"), "2.4", {"docs/THE-TRAP.md": historical}) == []


def test_a_roster_rule_cannot_match_a_pilot_sentence():
    """The two corpora have different denominators. The roster patterns all name
    "roster", "scorable relationship" or "of 239" so they cannot fire on a
    pilot document, which is why they need no skip list."""
    mod = _mod()
    pilot_prose = {"README.md": (
        "the permitted sources yielded 41 observations over 9 of 14 people, "
        "and the corpus holds 31 episodes")}
    for name in ("roster_observations", "roster_people_with_evidence",
                 "scorable_episodes", "coverage_saturation"):
        assert mod.find_mismatches(_rule(mod, name), "0", pilot_prose) == [], name


def test_a_rule_whose_artifact_key_vanished_fails_loudly():
    """Caught in the act: `coverage_saturation` was written against a key named
    `rungs` and the artifact calls it `ladder`. It raised KeyError rather than
    quietly extracting nothing and reporting the docs clean."""
    import pytest as _pytest
    mod = _mod()
    rule = _rule(mod, "coverage_saturation")
    with _pytest.raises(KeyError):
        rule.extract({"not_the_ladder": []})
