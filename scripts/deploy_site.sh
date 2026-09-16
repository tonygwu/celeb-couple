#!/usr/bin/env bash
# Publish the generated board to https://celebrities.tonygwu.com/ . FREE: no
# model quota, one Cloudflare deploy.
#
#   bash scripts/deploy_site.sh                  # publish the board on the Desktop
#   bash scripts/deploy_site.sh --dry-run        # stage + check ./site, publish nothing
#   bash scripts/deploy_site.sh --html path.html # publish some other rendered board
#
# The board itself comes from `bash scripts/refresh_boards.sh`, which writes
# $HOME/Desktop/punching-above-weight.html. This script does NOT render: it
# publishes whatever was rendered last, so the page that goes out is the page
# that was looked at.
#
# Everything here is a check on the ARTIFACT, not on wrangler's exit status. A
# deploy of an empty ./site succeeds and serves a 404 page, and a deploy of a
# half-written file succeeds and serves a broken board. Both look identical to
# `wrangler deploy; echo $?`, so each is refused here instead.
set -uo pipefail
cd "$(dirname "$0")/.."

HTML="${CELEB_BOARD_HTML:-$HOME/Desktop/punching-above-weight.html}"
SITE_URL="https://celebrities.tonygwu.com/"
TITLE="Celebrities Punching Above Their Weight"
DRY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --html) HTML="${2:?--html needs a path}"; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

die() { echo "REFUSING: $*" >&2; exit 1; }

# --- 1. Is the source actually the board? ------------------------------------
[ -f "$HTML" ] || die "no board at $HTML. Run: bash scripts/refresh_boards.sh"

BYTES=$(wc -c < "$HTML" | tr -d ' ')
# The board carries its whole dataset inline and has never been under 400KB. A
# file far below that is a truncated or half-written render, which is a real
# failure mode here: refresh_boards.sh reads caches while other stages write
# them. Refuse rather than publish a stub.
[ "$BYTES" -ge 400000 ] || die "$HTML is only ${BYTES} bytes; expected >=400000. Truncated render?"

grep -q "<title>${TITLE}</title>" "$HTML" \
  || die "$HTML has no <title>${TITLE}</title>; that is not this board"
grep -q 'const DATA' "$HTML" \
  || die "$HTML has no DATA blob; the board would render empty"

echo "source   ${HTML}"
echo "         ${BYTES} bytes, title and DATA blob present"

# --- 2. Stage it -------------------------------------------------------------
# ./site is gitignored and exists only to be the [assets] directory in
# wrangler.toml. It is rebuilt from scratch every time so a file left behind by
# an older deploy can never be served.
rm -rf site
mkdir -p site
cp "$HTML" site/index.html
echo "staged   ./site/index.html"

if [ "$DRY" -eq 1 ]; then
  echo "--dry-run: staged ./site, published nothing"
  exit 0
fi

# --- 3. Publish --------------------------------------------------------------
# wrangler.toml claims celebrities.tonygwu.com as a custom domain, so the first
# run of this creates the hostname and Cloudflare owns the DNS record for it.
npx --yes wrangler deploy
RC=$?
[ "$RC" -eq 0 ] || die "wrangler deploy exited ${RC}"

# --- 4. Prove the LIVE page is the board -------------------------------------
# A 200 proves a Worker answered, not that it answered with this board. Assert
# on the content. The first deploy of a new custom domain needs a certificate,
# so allow a few minutes of TLS failures before calling it broken.
echo "verifying ${SITE_URL}"
LIVE=""
for attempt in $(seq 1 40); do
  LIVE=$(curl -fsS --max-time 30 "$SITE_URL" 2>/dev/null) && break
  echo "  attempt ${attempt}: not serving yet (new hostnames need a certificate); waiting 15s"
  sleep 15
done

[ -n "$LIVE" ] || die "deployed, but ${SITE_URL} never served a response. Check the Cloudflare dashboard."

printf '%s' "$LIVE" | grep -q "<title>${TITLE}</title>" \
  || die "${SITE_URL} served something that is not this board (no matching <title>)"
printf '%s' "$LIVE" | grep -q 'const DATA' \
  || die "${SITE_URL} served the page WITHOUT its DATA blob"

LIVE_BYTES=$(printf '%s' "$LIVE" | wc -c | tr -d ' ')
echo "live     ${SITE_URL} -> ${LIVE_BYTES} bytes, title and DATA blob present"
echo "published $(date -u +%Y-%m-%dT%H:%M:%SZ)"
