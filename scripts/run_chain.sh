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
  run scripts/fetch_observations.py
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
  run scripts/write_m0_report.py
fi

printf '\n'
if (( fail )); then
  echo "chain finished WITH FAILURES" >&2
else
  echo "chain finished clean"
fi
exit "$fail"
