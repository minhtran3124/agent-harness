#!/bin/bash
# Scaffold the workflow's structural files into a repo — create-if-missing only.
# Replaces the scaffolding step of the removed bootstrap-xia2 skill: a deterministic,
# idempotent copy of the bundled structure templates. Never overwrites real content.
#
# Usage:  bash scripts/init-structure.sh [--root <dir>]
#   --root <dir>   Scaffold into <dir> instead of the repo root (used by tests).
# Exit 0 always (advisory setup helper); prints `created`/`exists` per file.
set -u

ROOT="."
[ "${1:-}" = "--root" ] && { ROOT="${2:?--root needs a path}"; }

SRC="$(cd "$(dirname "$0")/.." && pwd)/templates/structure"

# template (in templates/structure/)          → destination (relative to ROOT)
rows='
specs-README.md|specs/README.md
specs-STATE.md|specs/STATE.md
agent-memory-README.md|agent-memory/README.md
docs-solutions-README.md|docs/solutions/README.md
docs-solutions-INDEX.md|docs/solutions/INDEX.md
docs-solutions-critical-patterns.md|docs/solutions/critical-patterns.md
techstacks-README.md|techstacks/README.md
'

while IFS='|' read -r tmpl dest; do
  [ -z "$tmpl" ] && continue
  target="$ROOT/$dest"
  if [ -e "$target" ]; then
    printf '  exists   %s\n' "$dest"
  else
    mkdir -p "$(dirname "$target")"
    cp "$SRC/$tmpl" "$target"
    printf '  created  %s\n' "$dest"
  fi
done <<EOF
$rows
EOF

exit 0
