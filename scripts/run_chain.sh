#!/usr/bin/env bash
# Run the analysis chain in dependency order.
#
# The order lives here rather than only in AGENTS.md prose, because a chain
# order written down in two places drifts, and running a stage before the one
# it depends on produces a stale answer rather than an error.
#
#   bash scripts/run_chain.sh free     # no model calls; safe anywhere
#   bash scripts/run_chain.sh reports  # regenerate every report from artifacts
#   bash scripts/run_chain.sh all      # both
#
# Stages that SPEND MODEL QUOTA are deliberately NOT here. They need an account
# and a cap chosen by a human who has looked at `quotapick status`, and burying
# them in a convenience script is how an unattended run empties a window.
# See AGENTS.md for those.

set -uo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
MODE=${1:-all}
fail=0

run() {
  printf '\n=== %s\n' "$*"
  if ! "$PY" "$@"; then
    echo "FAILED: $*" >&2
    fail=1
  fi
}

if [[ "$MODE" == "free" || "$MODE" == "all" ]]; then
  run scripts/fetch_records.py
  run scripts/build_episodes.py
  run scripts/build_partner_universe.py
  run scripts/fetch_onscreen_candidates.py
  run scripts/fetch_observations.py
  # Immediately after the fetch, because the fetch REWRITES observations.json
  # from the award/ranked tables alone and drops any prose mentions previously
  # folded in. Running fetch_observations.py by hand cost this corpus 8 of its
  # 41 observations, silently -- the count only surfaced because the doc audit
  # caught "Women hold 17" against a corpus that now said 16.
  # Merging is idempotent (tests/test_merge_idempotent.py), so a re-run adds
  # nothing and this is safe to do every time.
  for m in data/pilot/observations/prose_mentions.json \
           data/pilot/observations/prose_mentions_partners.json; do
    [ -f "$m" ] && run scripts/merge_prose_mentions.py --mentions "$m"
  done
  # After the merge, so it sees the corpus the reports will actually read.
  # This is the only stage that checks the observations against the live pages
  # they were extracted from; everything downstream takes them on trust.
  # First of the three verifiers, because a wrong Q-id makes every fact
  # fetched under it wrong, and the fetchers above have already used them.
  run scripts/verify_identities.py
  run scripts/verify_observations.py
  # Needs episodes.json. Feeds the review sheet in the reports pass, so it has
  # to run before it rather than beside it.
  run scripts/corroborate_relationships.py
fi

if [[ "$MODE" == "reports" || "$MODE" == "all" ]]; then
  # These read whatever scored artifacts exist. They skip nothing silently:
  # a missing input names the command that produces it and exits non-zero.
  run scripts/joint_coverage.py
  run scripts/evidence_density.py
  run scripts/alignment_gap.py
  run scripts/partner_eligibility.py
  run scripts/shape_confound.py
  run scripts/gender_shape_confound.py
  run scripts/grounding_audit.py
  run scripts/offset_diagnostic.py
  # Only if the roster-scale artifacts exist. docs/SCALING.md compares the
  # pilot against the 100-roster, so it goes stale whenever the PILOT grows --
  # which it did, leaving a table reading 35 observations against a corpus of
  # 41 while the roster column stayed right.
  # Before scaling_report, which reads its ladder. It was in no chain at all,
  # so its artifact still described a 239-episode corpus after the corpus
  # became 228 -- and its ceiling is the project's most optimistic number.
  [ -f data/roster100/records/episodes.json ] && run scripts/source_requirement.py
  [ -f data/roster100/run/joint_real_life.json ] && run scripts/scaling_report.py
  # Same gate, same reason. docs/REACHABLE-PRODUCTS.md went stale the moment
  # mirrored episode duplicates were collapsed -- it read 239 scorable roster
  # episodes against a corpus that now said 228 -- because nothing re-ran it.
  [ -f data/roster100/run/joint_real_life.json ] && run scripts/reachable_products.py
  run scripts/relationship_review.py
  run scripts/conclusion_robustness.py
  run scripts/verify_trap.py
  run scripts/cross_run_stability.py
  run scripts/write_m0_report.py
  # Last, because it checks the prose against the artifacts every stage above
  # just rewrote. Running it earlier would audit the previous run's numbers.
  run scripts/audit_doc_numbers.py
fi

printf '\n'
if (( fail )); then
  echo "chain finished WITH FAILURES" >&2
else
  echo "chain finished clean"
fi
exit "$fail"
