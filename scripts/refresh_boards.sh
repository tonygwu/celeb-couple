#!/usr/bin/env bash
# Rebuild the IMDb boards from whatever has landed so far. FREE.
#
# Safe to run WHILE identify_couples.py and score_person_periods.py are still
# writing: every stage is read-only over their caches. A stage that reads a
# cache mid-write sees a truncated JSON document, so each retries once. Runs
# started before packages/llmkit/atomic.py existed still use the truncating
# write, which is exactly the window the retry covers.
#
# The Wikidata bridge is NOT run every time. It is a network fetch for a
# mapping that does not move, so it runs only when new people have appeared.
set -uo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
fail=0

run() {
  local label="$1"; shift
  if ! "$@" > /tmp/refresh_stage.log 2>&1; then
    echo "  $label FAILED (retrying once, it may have read a cache mid-write)" >&2
    sleep 3
    if ! "$@" > /tmp/refresh_stage.log 2>&1; then
      echo "  $label FAILED twice:" >&2; tail -3 /tmp/refresh_stage.log >&2
      fail=1; return 1
    fi
  fi
  tail -1 /tmp/refresh_stage.log
}

echo "=== refresh $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

# How many people in board rows still have no Wikidata id? Re-bridge only then.
need_bridge=$($PY - <<'PYEOF'
import json, pathlib
try:
    b = json.load(open("data/imdb/person_bridge.json"))
    p = json.load(open("data/imdb/imdb_pairings.json"))
    missing = p["counts"]["dropped"].get("no Wikidata id for one side", 0)
    print(1 if missing > 0 else 0)
except Exception:
    print(1)
PYEOF
)
if [ "$need_bridge" = "1" ]; then
  run "bridge   " $PY scripts/resolve_imdb_people.py
else
  echo "  bridge    up to date, skipped (no unbridged people)"
fi

run "pairings " $PY scripts/build_imdb_pairings.py
run "gradings " $PY scripts/build_person_gradings.py
run "boards   " $PY scripts/rebuild_boards.py \
      --graph data/imdb/imdb_pairings.json \
      --cache data/imdb/person_period_cache_opus.json \
      --cache data/roster100/run/person_period_cache.json \
      --out "$HOME/Desktop/punching-above-weight.html"

if (( fail )); then echo "refresh finished WITH FAILURES" >&2; else echo "refresh clean"; fi
exit "$fail"
