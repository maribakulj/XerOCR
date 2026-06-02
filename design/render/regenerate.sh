#!/usr/bin/env bash
# Regenerate ALL reference screenshots in ../screenshots/ from the single
# source of truth (../tokens.css + ../picarones.css + ../*.jsx).
#
# Network: only npm (registry.npmjs.org) to fetch React/Babel. The browser is
# NOT downloaded (we reuse a pre-installed Chromium via CHROMIUM_PATH); set
# PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 keeps `npm install` offline-friendly.
set -euo pipefail
cd "$(dirname "$0")"

export PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1
npm install --no-audit --no-fund

# CHROMIUM_PATH defaults inside render.js to the Playwright build; override if needed:
#   CHROMIUM_PATH=/usr/bin/chromium ./regenerate.sh
for v in overview by-engine by-document crosses; do
  node render.js "$v"
done
echo "screenshots regenerated in ../screenshots/"
