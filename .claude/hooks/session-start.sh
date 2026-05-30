#!/bin/bash
# SessionStart hook — installe les dépendances pour que tests et linters
# tournent dans les sessions Claude Code on the web. Idempotent, non-interactif.
set -euo pipefail

# Sessions distantes (web) uniquement : le dev local gère son propre env.
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-.}"
python3 -m pip install --quiet --root-user-action=ignore -e ".[dev]" 1>&2
