#!/usr/bin/env bash
# Render web/og-card.html to web/og.png at 1200x630. FREE.
#
# This is the picture Twitter, LinkedIn and Slack show when someone posts the
# board. It is deliberately STATIC -- no scores, no names -- so it cannot go
# stale as the corpus grows. Re-run only when web/og-card.html changes.
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME="${CHROME_BIN:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
[ -x "$CHROME" ] || { echo "no Chrome at $CHROME; set CHROME_BIN" >&2; exit 1; }
"$CHROME" --headless --disable-gpu --no-sandbox --hide-scrollbars \
  --force-device-scale-factor=1 --virtual-time-budget=4000 \
  --window-size=1200,630 --screenshot=web/og.png "file://$PWD/web/og-card.html" >/dev/null 2>&1
file web/og.png | grep -q "1200 x 630" || { echo "wrong size" >&2; exit 1; }
echo "wrote web/og.png ($(wc -c < web/og.png | tr -d ' ') bytes)"
