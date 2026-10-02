#!/usr/bin/env bash
# Install and PROVE every dependency, locally or at the start of a cloud run.
# Anything but a final "READY" = do not post this run.
#
#   bash scripts/setup.sh            # from the skill folder
#
# Needs: python3 (3.10+), node (18+), and KIE_API_KEY (or ~/.config/kie/api_key) for art + image hosting.
# Instagram is checked separately (composio_connect.py whoami, or ig_workbench.py posted-code in the cloud).
set -uo pipefail
cd "$(dirname "$0")/.."
ok(){ echo "OK    $*"; }; bad(){ echo "FAIL  $*"; FAILED=1; }; FAILED=0
LOG="${TMPDIR:-/tmp}/instagram-posts-setup.log"; : > "$LOG"

KEY="${KIE_API_KEY:-}"; [ -z "$KEY" ] && [ -f ~/.config/kie/api_key ] && KEY="$(cat ~/.config/kie/api_key)"
[ -n "$KEY" ] && ok "kie.ai key found" || bad "kie.ai key missing: set KIE_API_KEY (https://kie.ai)"

[ -x venv/bin/python ] || python3 -m venv venv >>"$LOG" 2>&1
venv/bin/pip install -q -r requirements.txt >>"$LOG" 2>&1 && ok "python deps (venv/)" || bad "pip install -r requirements.txt (see $LOG)"

if npm install --no-audit --no-fund --silent >>"$LOG" 2>&1 && \
   { npx playwright install --with-deps chromium >>"$LOG" 2>&1 || npx playwright install chromium >>"$LOG" 2>&1; }; then
  ok "playwright chromium"; else bad "playwright chromium (see $LOG)"; fi

if [ -n "$KEY" ]; then
  CR=$(curl -s -m 20 -H "Authorization: Bearer $KEY" https://api.kie.ai/api/v1/chat/credit)
  echo "$CR" | grep -q '"code":200' && ok "kie.ai credits: $(echo "$CR" | sed -E 's/.*"data":([0-9.]+).*/\1/')" || bad "kie.ai: $(echo "$CR" | head -c 200)"
fi

curl -s -o /dev/null -m 20 -w "%{http_code}" -L "https://news.google.com/rss/search?q=test" | grep -q 200 && ok "Google News reachable" || bad "Google News unreachable"
venv/bin/python scripts/datasource.py stats >/dev/null 2>>"$LOG" && ok "data source loads" || bad "data source (see $LOG)"

[ "$FAILED" = 0 ] && echo "READY" || { echo "NOT READY: post nothing this run"; exit 1; }
