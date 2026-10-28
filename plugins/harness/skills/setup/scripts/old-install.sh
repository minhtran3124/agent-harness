#!/bin/bash
# Find the copy that the pre-plugin installer put into a project's .claude/ folder.
# Usage: old-install.sh <project-dir>                 print the paths to remove, one per line
#        old-install.sh --strip-hooks <settings.json> remove the old hook entries from settings
# Never deletes a path. The caller shows the list to the owner and deletes only after approval.
# Harness-owned means: named like a file this plugin ships. Anything else is the project's own.
# Exit: 0 always for the list mode (an empty list means no old install); --strip-hooks needs jq.
set -u

if [ "${1:-}" = "--strip-hooks" ]; then
  f=${2:?usage: old-install.sh --strip-hooks <settings.json>}
  command -v jq >/dev/null 2>&1 || { echo "old-install: jq is required" >&2; exit 3; }
  [ -f "$f" ] || { echo "no $f"; exit 0; }
  tmp=$(mktemp "$f.XXXXXX")
  # Drop each hook whose command points into .claude/hooks/, then any group left empty.
  if jq '(.hooks // {}) as $h | if ($h | length) == 0 then . else
      .hooks |= (with_entries(.value |= (map(.hooks |= map(select((.command // "") | test("\\.claude/hooks/") | not))) | map(select((.hooks | length) > 0))))
                 | with_entries(select((.value | length) > 0))) end' "$f" > "$tmp"; then
    mv "$tmp" "$f"; echo "removed old .claude/hooks entries from $f"
  else
    rm -f "$tmp"; echo "old-install: $f is not valid JSON; not touching it" >&2; exit 2
  fi
  exit 0
fi

PROJ=${1:?usage: old-install.sh <project-dir>}
PLUGIN=$(cd "$(dirname "$0")/../../.." && pwd)
C="$PROJ/.claude"
[ -d "$C" ] || exit 0

emit() { [ -e "$1" ] && printf '%s\n' "$1"; return 0; }

emit "$C/.harness-deployed"
for d in "$PLUGIN"/skills/*/; do emit "$C/skills/$(basename "$d")"; done
for f in "$PLUGIN"/agents/*.md; do emit "$C/agents/$(basename "$f")"; done
for f in "$PLUGIN"/hooks/*.sh; do emit "$C/hooks/$(basename "$f")"; done
emit "$C/workflows/ship.js"
for f in "$PLUGIN"/scripts/*; do emit "$C/scripts/$(basename "$f")"; done
emit "$C/scripts/render_skill_prompt.py"
emit "$C/templates"
for p in "$C"/.harness-backup-* "$C"/*.harness-incoming "$PROJ"/.harness-source; do emit "$p"; done
# The old rule copy stays until the session-rules hook is confirmed to deliver the rule.
exit 0
