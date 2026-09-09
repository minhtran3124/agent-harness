#!/bin/bash
# PostToolUse hook: run ruff --fix + ruff format on any edited .py file.
# Non-blocking — always exits 0.

INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Repo root: runtime answer FIRST. The old order consulted CLAUDE_PROJECT_DIR only after the
# SCRIPT_DIR probe had already returned a wrong-but-successful answer — see
# specs/fix-hook-project-root-resolution. SCRIPT_DIR stays, but only to locate this hook's libs.
REPO_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
NORMALIZER="$SCRIPT_DIR/lib/normalize-tool-input.py"
if command -v python3 >/dev/null 2>&1 && [ -f "$NORMALIZER" ]; then
  NORMALIZED=$(printf '%s' "$INPUT" | python3 "$NORMALIZER" --root "$REPO_DIR" 2>/dev/null)
else
  NORMALIZED='{"status":"unknown","paths":[],"diagnostics":["normalizer-unavailable"]}'
fi
STATUS=$(printf '%s' "$NORMALIZED" | jq -r '.status // "unknown"' 2>/dev/null)
PATHS=$(printf '%s' "$NORMALIZED" | jq -r '.paths[]?' 2>/dev/null)

while IFS= read -r rel; do
  [ -n "$rel" ] || continue
  case "$rel" in
    *.py)
      file="$REPO_DIR/$rel"
      [ -f "$file" ] && { ruff check --fix "$file"; ruff format "$file"; } >/dev/null 2>&1 || true
      ;;
  esac
done <<EOF
$PATHS
EOF

if [ "$STATUS" != "known" ]; then
  DIAG=$(printf '%s' "$NORMALIZED" | jq -r '.diagnostics | join(", ")' 2>/dev/null)
  jq -cn --arg d "${DIAG:-unparsed payload}" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:("ruff-on-edit: edit payload was only partially understood (" + $d + "); valid Python paths were processed, but formatting coverage is incomplete.")}}' 2>/dev/null \
    || echo "[RUFF-ON-EDIT] partial/unknown edit payload: ${DIAG:-unparsed payload}" >&2
fi
exit 0
