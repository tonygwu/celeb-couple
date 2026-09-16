"""No script reads a scored artifact without the provenance check.

The stale-contract guard lives inside ``require`` precisely so that no caller
has to remember it. Two scripts read artifacts a different way and therefore
skipped it: ``write_m0_report.py``, which defines its own ``load``, and
``audit_doc_numbers.py``, which called ``json.loads`` inline.

That was not theoretical. During the 2026-09-14 contract bump every
require()-based stage correctly refused the stale corpus, ``run_chain.sh``
recorded each failure and carried on, and ``write_m0_report.py`` then rendered
docs/M0-REPORT.md from scores no rubric on disk produced. The deliverable is
the worst possible place for a provenance check to be optional.

This test is about the CLASS, not those two files. A third script that reads
artifacts its own way fails here rather than being found by accident.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPTS = REPO / "scripts"

#: Reading an artifact from disk. Either spelling counts.
_READS_ARTIFACT = re.compile(r"json\.loads?\s*\(|json\.load\s*\(")

#: Either route to the check: ``require`` runs it, or the script calls it.
_HAS_GUARD = ("from packages.llmkit.artifacts import", "refuse_stale_contract")

#: Scripts that legitimately read JSON that no rubric produced.
#:
#: Each entry needs a reason. "It was failing" is not one -- an exemption
#: without a reason is how a guard rots into a formality.
_EXEMPT = {
    # Writes artifacts rather than analysing them; the contract it stamps is
    # the one it just computed from the rubrics on disk.
    "resolve_roster.py": "reads a name list, produces the roster; no scores involved",
    "fetch_records.py": "reads the cohort file and Wikidata; nothing scored yet",
    "fetch_observations.py": "reads records and Wikipedia; nothing scored yet",
    "fetch_onscreen_candidates.py": "reads records and Wikidata; nothing scored yet",
    "build_episodes.py": "arithmetic over relationship records; no rubric involved",
    "build_partner_universe.py": "derived from episodes; no rubric involved",
    "verify_identities.py": "checks Wikidata ids against a roster file",
    "verify_observations.py": "re-fetches source pages; reads observations, not scores",
    "corroborate_relationships.py": "reads episodes and Wikipedia prose",
    "merge_prose_mentions.py": "merges observation files; the contract check on the "
                               "mentions artifact belongs to its producer",
    # The four below read observations, the cohort file and joint coverage, and
    # then WRITE scores stamped with the contract they just computed from the
    # rubrics on disk. None of them reads a previously scored artifact, so
    # there is no stored contract id for them to check.
    #
    # run_stress.py and measure_rater_noise.py are NOT here. Both do read a
    # previously scored artifact -- the rater-noise floor and their own
    # --recompute input -- and both now check it.
    "classify_romance.py": "reads onscreen candidates; writes romance verdicts",
    "extract_prose_mentions.py": "reads the cohort and Wikipedia; writes mentions",
    "run_pilot.py": "reads records and observations; writes a fresh scoring run",
    "score_evidenced.py": "reads observations, cohort and joint coverage; writes scores",
    # Reads docs/seed-roster.json, a HAND-WRITTEN roster, and the external IMDb
    # dumps. Neither is produced by a rubric, so there is no contract id on
    # either and nothing that could go stale. It reads no scored artifact.
    "build_imdb_graph.py": "reads a hand-written roster and the IMDb dumps; writes a pairing graph",
}


def _scripts() -> list[Path]:
    return [p for p in sorted(SCRIPTS.glob("*.py")) if p.name != "__init__.py"]


def test_there_are_scripts_to_check():
    assert len(_scripts()) >= 30, "glob found almost nothing; this test proves nothing"


def test_every_artifact_reader_runs_the_contract_check():
    offenders = []
    for p in _scripts():
        src = p.read_text()
        if p.name in _EXEMPT:
            continue
        if not _READS_ARTIFACT.search(src):
            continue
        if any(marker in src for marker in _HAS_GUARD):
            continue
        offenders.append(p.name)
    assert not offenders, (
        "these scripts read JSON artifacts without the stale-contract check: "
        f"{offenders}. Read them through packages.llmkit.artifacts.require, or "
        "call refuse_stale_contract directly if a missing file must stay "
        "allowed. If the script genuinely reads nothing a rubric produced, add "
        "it to _EXEMPT here WITH a reason."
    )


def test_every_exemption_names_a_script_that_exists():
    # An exemption for a deleted script silently widens to nothing, but an
    # exemption for a RENAMED one silently stops covering the new name.
    missing = [n for n in _EXEMPT if not (SCRIPTS / n).exists()]
    assert not missing, f"exemptions naming scripts that are gone: {missing}"


def test_the_two_known_bypasses_are_fixed():
    # Named explicitly, because these are the two that actually shipped.
    for name in ("write_m0_report.py", "audit_doc_numbers.py"):
        src = (SCRIPTS / name).read_text()
        assert "refuse_stale_contract" in src, f"{name} lost its contract check"
