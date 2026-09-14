"""Absent from the corpus, or absent from the reachable sources?

The report says four of fourteen cohort members carry no observation. "We
looked and found nothing" invites someone to look harder; "no permitted route
reaches evidence about this person" is a finding. Nothing distinguished them.

The risk in the checker is over-claiming, and it over-claimed twice while being
written. The prose match keyed on the list label's first word, so "Most" from
"Most Beautiful" matched almost any long article and flagged Adam Sandler. And
the verdict was first called `absent_from_every_permitted_source`, which is
more than the evidence carries: Wikipedia reproduces only the winner of Maxim
and Esquire and only FHM's top ten.

No test here touches the network.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def _mod():
    spec = importlib.util.spec_from_file_location(
        "absence_audit", REPO / "scripts/absence_audit.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def test_the_surname_helper_takes_the_last_word():
    assert _mod().surname("Ana de Armas") == "Armas"
    assert _mod().surname("Zendaya") == "Zendaya"


def test_every_source_the_pipeline_reads_is_searched():
    """A source missing from SOURCES makes an absence verdict wrong, because
    the person could be named in the table nobody looked at."""
    m = _mod()
    labels = {label for _, _, label in m.SOURCES}
    assert len(m.SOURCES) == 5
    assert {"Sexiest Man Alive", "Most Beautiful", "Maxim Hot 100",
            "Sexiest Woman Alive", "FHM 100 Sexiest Women"} == labels


def test_the_verdict_does_not_claim_more_than_reachability():
    """`absent_from_every_permitted_source` was the first wording, and it
    claims the person was never rated. Wikipedia carries only the winner of
    Maxim and Esquire and only FHM's top ten, so the evidence cannot support
    that. The assertion is on the emitted verdict STRING, because the old
    phrase deliberately survives in the comment that explains the change.
    """
    import json
    path = REPO / "data/pilot/run/absence_audit.json"
    if not path.exists():
        pytest.skip("data/ is gitignored; run scripts/absence_audit.py")
    verdicts = {r["verdict"] for r in json.loads(path.read_text())["rows"]}
    assert verdicts, "no rows, so this asserts nothing"
    assert verdicts <= {"no_permitted_route_reaches_them",
                        "named_somewhere_investigate"}, verdicts
    assert "absent_from_every_permitted_source" not in verdicts


def test_the_limit_is_stated_in_the_module_and_the_artifact_note():
    """A reader meeting this verdict must meet the caveat at the same time."""
    m = _mod()
    doc = m.__doc__ or ""
    assert "top ten" in doc and "number 37" in doc, (
        "the module must say Wikipedia does not reproduce these lists in full")


def test_the_recorded_run_agrees_with_the_corpus():
    import json
    path = REPO / "data/pilot/run/absence_audit.json"
    obs = REPO / "data/pilot/observations/observations.json"
    if not (path.exists() and obs.exists()):
        pytest.skip("data/ is gitignored; run scripts/absence_audit.py")
    payload = json.loads(path.read_text())
    have = {o["person_id"] for o in json.loads(obs.read_text())["observations"]}
    assert payload["rows"], "nothing was checked, so the counts below are vacuous"
    for r in payload["rows"]:
        assert r["wikidata_qid"] not in have, (
            f"{r['person']} has observations and should not be in this audit")
    assert payload["with_observations"] + payload["checked"] == payload["cohort_size"]


def test_no_audited_person_is_a_pipeline_gap():
    """A person the tables DO name but the corpus lacks is a pipeline bug, not
    a source gap, and must not be reported as absence."""
    import json
    path = REPO / "data/pilot/run/absence_audit.json"
    if not path.exists():
        pytest.skip("data/ is gitignored")
    gaps = [r["person"] for r in json.loads(path.read_text())["rows"]
            if r["verdict"] == "named_somewhere_investigate"]
    assert gaps == [], (
        f"these are named in a permitted source but carry no observation, "
        f"which is a pipeline gap rather than a source gap: {gaps}")


# ---------------------------------------------------------------------------
# the partner universe
# ---------------------------------------------------------------------------

def test_the_partner_audit_only_covers_people_the_project_would_rate():
    """Someone classified not_a_public_figure_do_not_rate is not missing
    evidence. The project has decided not to look, and auditing them would
    report a gap where there is a policy."""
    import json
    path = REPO / "data/pilot/run/absence_audit_partners.json"
    elig = REPO / "data/pilot/records/partner_eligibility.json"
    if not (path.exists() and elig.exists()):
        pytest.skip("data/ is gitignored; run the chain first")
    payload = json.loads(path.read_text())
    assert payload["source"] == "partners"
    status = {r["qid"]: r["status"]
              for r in json.loads(elig.read_text())["partners_detail"]}
    assert payload["rows"], "no partners audited, so the counts are vacuous"
    for r in payload["rows"]:
        assert status[r["wikidata_qid"]] == "public_figure_no_evidence_found", (
            f"{r['person']} is {status[r['wikidata_qid']]} and should not be "
            "in an evidence-absence audit")


def test_a_surname_only_hit_is_not_counted_as_being_named():
    """Pauletta Pearson Washington matches "Washington" in two tables, because
    Denzel Washington is in them. A surname is not a person."""
    import json
    path = REPO / "data/pilot/run/absence_audit_partners.json"
    if not path.exists():
        pytest.skip("data/ is gitignored")
    for r in json.loads(path.read_text())["rows"]:
        if r["surname_only_in"] and not r["named_in_source_tables"] \
                and not r["publisher_named_in_own_article"]:
            assert r["verdict"] == "no_permitted_route_reaches_them", (
                f"{r['person']} was counted as named on a surname match alone")


def test_the_partner_audit_flags_rather_than_decides():
    """Peter Horton's article names People's "50 Most Beautiful People" with no
    year, so the corpus correctly holds nothing. The audit must surface him for
    a human rather than either ignoring him or inventing an observation."""
    import json
    path = REPO / "data/pilot/run/absence_audit_partners.json"
    if not path.exists():
        pytest.skip("data/ is gitignored")
    rows = {r["person"]: r for r in json.loads(path.read_text())["rows"]}
    horton = rows.get("Peter Horton")
    if horton is None:
        pytest.skip("Peter Horton is not in this partner universe")
    assert horton["verdict"] == "named_somewhere_investigate"
    assert horton["publisher_named_in_own_article"] == ["Most Beautiful"]
