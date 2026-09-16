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
# on the content.
#
# The address is resolved through a PUBLIC resolver and handed to curl with
# --resolve, rather than left to the system resolver. That is not tidiness. The
# first deploy of this site was verified on a machine whose resolver had cached
# the NXDOMAIN from before the hostname existed, so curl could not resolve a
# name that 1.1.1.1 and 8.8.8.8 were both already answering, and the script
# reported the live site broken when it was serving correctly. A stale negative
# cache is local to one machine; what a public resolver returns is what a
# visitor gets, and that is the thing worth checking.
HOSTNAME_ONLY=$(printf '%s' "$SITE_URL" | sed -e 's|^https://||' -e 's|/.*$||')
echo "verifying ${SITE_URL}"

# The response goes to a FILE and is grepped there, never piped into grep.
# `printf '%s' "$body" | grep -q PATTERN` looks equivalent and is not: grep -q
# exits the moment it matches, printf gets SIGPIPE, and under `set -o pipefail`
# the pipeline reports 141. That reads as "the live page is wrong" on exactly
# the runs where the page is right. It failed this script once, on a
# byte-identical page.
LIVE_FILE=$(mktemp -t celeb-deploy-live)
trap 'rm -f "$LIVE_FILE"' EXIT
GOT=0
for attempt in $(seq 1 40); do
  # Re-resolve every attempt: on a brand-new hostname the record itself is
  # what has not appeared yet.
  IP=$(dig +short @1.1.1.1 "$HOSTNAME_ONLY" A 2>/dev/null | grep -E '^[0-9.]+$' | head -1)
  if [ -z "$IP" ]; then
    echo "  attempt ${attempt}: ${HOSTNAME_ONLY} does not resolve publicly yet; waiting 15s"
    sleep 15; continue
  fi

  if curl -fsS --max-time 30 --resolve "${HOSTNAME_ONLY}:443:${IP}" \
          -o "$LIVE_FILE" "$SITE_URL" 2>/dev/null; then
    GOT=1; break
  fi
  # Resolves but will not serve: on a new custom domain this is the certificate
  # being issued, which takes a few minutes.
  echo "  attempt ${attempt}: resolves to ${IP} but not serving yet (a new hostname needs a certificate); waiting 15s"
  sleep 15
done

[ "$GOT" -eq 1 ] || die "deployed, but ${SITE_URL} never served a response. Check the Cloudflare dashboard."

grep -q "<title>${TITLE}</title>" "$LIVE_FILE" \
  || die "${SITE_URL} served something that is not this board (no matching <title>)"
grep -q 'const DATA' "$LIVE_FILE" \
  || die "${SITE_URL} served the page WITHOUT its DATA blob"

# The strongest check available: the bytes on the wire against the bytes that
# were rendered. A match means the published page IS the reviewed page, not
# merely a page with the same title.
LIVE_BYTES=$(wc -c < "$LIVE_FILE" | tr -d ' ')
if [ "$(shasum -a256 < "$LIVE_FILE" | cut -d' ' -f1)" = "$(shasum -a256 < "$HTML" | cut -d' ' -f1)" ]; then
  echo "live     ${SITE_URL} -> ${LIVE_BYTES} bytes, byte-identical to the rendered board"
else
  echo "live     ${SITE_URL} -> ${LIVE_BYTES} bytes, title and DATA blob present"
  echo "         NOTE: bytes differ from ${HTML}. An edge cache may still hold the previous version."
fi
echo "published $(date -u +%Y-%m-%dT%H:%M:%SZ)"
