"""Load a pipeline artifact, or say clearly what to run to produce it.

A fresh clone has no data/ -- it is gitignored, because the corpus lives in a
separate private repository. Every analysis script therefore fails in a fresh
clone, which is correct. What is NOT correct is failing with a bare
FileNotFoundError traceback, because the next agent then has to read the script
to work out which command produces the missing file.
"""

from __future__ import annotations

import json
from pathlib import Path

from packages.llmkit.contract import refuse_stale_contract

__all__ = ["MissingArtifact", "require", "PRODUCERS"]


class MissingArtifact(SystemExit):
    """Exits with a message naming the command that produces the file."""


#: Which command produces which artifact. Keep in step with AGENTS.md.
PRODUCERS = {
    "data/pilot/records/relationship_candidates.json": "scripts/fetch_records.py",
    "data/pilot/records/episodes.json": "scripts/build_episodes.py",
    "data/pilot/records/onscreen_candidates.json": "scripts/fetch_onscreen_candidates.py",
    "data/pilot/records/romance.json": "scripts/classify_romance.py  [spends quota]",
    "data/pilot/records/partner_universe.json": "scripts/build_partner_universe.py",
    "data/pilot/records/partner_eligibility.json": "scripts/partner_eligibility.py",
    # NOT bare fetch_observations.py: it rewrites this file from the award and
    # ranked tables alone and drops any prose mentions previously merged in,
    # which cost this corpus 8 of its 41 observations once. The chain runs the
    # fetch and both merges in order.
    "data/pilot/observations/observations.json":
        "bash scripts/run_chain.sh free  (fetch_observations.py alone drops merged prose mentions)",
    "data/pilot/observations/prose_mentions.json": "scripts/extract_prose_mentions.py  [spends quota]",
    "data/pilot/run/evidenced_scores.json": "scripts/score_evidenced.py  [spends quota]",
    "data/pilot/run/joint_with_nearby.json": "scripts/joint_coverage.py",
    "data/pilot/run/rater_noise.json": "scripts/measure_rater_noise.py  [spends quota]",
    "data/pilot/stress/stress_report.json": "scripts/run_stress.py  [spends quota]",
    "data/pilot/run/shape_confound.json": "scripts/shape_confound.py",
    "data/pilot/run/gender_shape_confound.json": "scripts/gender_shape_confound.py",
    "data/pilot/run/evidence_density.json": "scripts/evidence_density.py",
    "data/pilot/run/cross_run_stability.json": "scripts/cross_run_stability.py",
    "data/pilot/run/grounding_audit.json": "scripts/grounding_audit.py",
    "data/pilot/run/offset_diagnostic.json": "scripts/offset_diagnostic.py",
    "data/pilot/run/alignment_gap.json": "scripts/alignment_gap.py",
    "docs/pilot-cohort.json": "committed to the repository; nothing produces it",
    "docs/roster-100.json": "scripts/resolve_roster.py",
    # The roster-scale corpus uses the same scripts with --cohort/--out paths.
    # See "Running the roster-scale chain" in AGENTS.md.
    "data/roster100/records/episodes.json":
        "scripts/build_episodes.py --cohort docs/roster-100.json  (see AGENTS.md)",
    "data/roster100/records/partner_universe.json":
        "scripts/build_partner_universe.py --cohort docs/roster-100.json  (see AGENTS.md)",
    "data/roster100/observations/observations.json":
        "scripts/fetch_observations.py --cohort docs/roster-100.json  (see AGENTS.md)",
    "data/roster100/run/evidence_density.json":
        "scripts/evidence_density.py --out data/roster100/run/  (see AGENTS.md)",
    "data/roster100/run/joint_real_life.json":
        "scripts/scaling_report.py  (see AGENTS.md)",
    "data/roster100/run/joint_scores.json":
        "scripts/score_roster_joint.py  [spends quota]",
    # Plan v4.
    "data/roster100/run/m1_slice.json": "scripts/select_m1_slice.py",
    "data/roster100/run/pairing_scores.json":
        "scripts/score_pairings.py  [spends quota]",
    "data/roster100/records/onscreen_candidates.json":
        "scripts/fetch_onscreen_candidates.py --cohort docs/roster-100.json  (see AGENTS.md)",
    "data/roster100/run/person_period_cache.json":
        "scripts/score_person_periods.py  [spends quota]",
    "data/roster100/run/person_period_cache_astra.json":
        "scripts/score_person_periods.py --judges astra  [spends quota]",
    "data/roster100/run/extra_gradings.json":
        "gradings from one-off comparison runs; no single script owns it",
    "data/roster100/run/person_gradings.json": "scripts/build_person_gradings.py",
    "data/imdb/seed_graph.json": "scripts/build_imdb_graph.py --dumps <dir>",
    "data/imdb/couples_cache.json": "scripts/identify_couples.py  [spends quota]",
    "data/imdb/person_bridge.json": "scripts/resolve_imdb_people.py",
    "data/imdb/imdb_pairings.json": "scripts/build_imdb_pairings.py",
    "data/imdb/person_period_cache_opus.json":
        "scripts/score_person_periods.py --from-scores data/imdb/imdb_pairings.json  [spends quota]",
}


def require(repo: Path, relative: str, *, check_contract: bool = True) -> dict:
    """Read a JSON artifact, or exit with the command that creates it.

    Also refuses an artifact whose grading contract no longer exists on disk.
    That check lives HERE, rather than in the nine analysis scripts that read
    scored artifacts, because a guard each caller must remember to invoke is a
    guard a new caller silently skips -- which is exactly what happened to
    ``refuse_mixed_contracts``. Pass ``check_contract=False`` only to inspect
    a stale artifact deliberately, such as when deciding whether to re-score.
    """
    path = repo / relative
    if path.exists():
        data = json.loads(path.read_text())
        if check_contract:
            refuse_stale_contract(repo, relative, data)
        return data
    producer = PRODUCERS.get(relative, "the pipeline stage that writes it")
    raise MissingArtifact(
        f"\nMissing artifact: {relative}\n"
        f"  Produce it with: {producer}\n"
        f"  data/ is gitignored, so a fresh clone has none of it. "
        f"See AGENTS.md for the full chain order.\n"
    )
