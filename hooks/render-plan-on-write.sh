#!/bin/bash
# PostToolUse(Write|Edit): auto-render specs/<slug>/PLAN.md -> PLAN.html (deterministic, no LLM).
# Also injects/refreshes the tracked "At a glance" block in PLAN.md itself (--summarize).
# Non-blocking: every edge case exits 0. Won't loop: render_plan.py writes via subprocess
# (not the Write/Edit tool), so PostToolUse does not re-fire; and --summarize is a no-op
# when the block is already current.

command -v jq >/dev/null 2>&1 || exit 0
command -v python3 >/dev/null 2>&1 || exit 0

INPUT=$(cat /dev/stdin)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Repo root: runtime answer first, git-from-CWD second. NEVER from SCRIPT_DIR — see
# specs/fix-hook-project-root-resolution (silent wrong-repo resolution with exit 0).
REPO_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
if [ -z "$REPO_DIR" ]; then
  echo "[render-plan] project root unknown — PLAN.html render skipped." >&2
  exit 0
fi
NORMALIZER="$SCRIPT_DIR/lib/normalize-tool-input.py"
if [ -f "$NORMALIZER" ]; then
  NORMALIZED=$(printf '%s' "$INPUT" | python3 "$NORMALIZER" --root "$REPO_DIR" 2>/dev/null)
else
  NORMALIZED='{"status":"unknown","paths":[],"diagnostics":["normalizer-unavailable"]}'
fi
STATUS=$(printf '%s' "$NORMALIZED" | jq -r '.status // "unknown"' 2>/dev/null)
PATHS=$(printf '%s' "$NORMALIZED" | jq -r '.paths[]?' 2>/dev/null)

RENDER="$REPO_DIR/skills/visual-planner/render_plan.py"
MESSAGES=""
if [ -f "$RENDER" ]; then
  while IFS= read -r rel; do
    [ -n "$rel" ] || continue
    case "$rel" in specs/*/PLAN.md) ;; *) continue ;; esac
    FILE="$REPO_DIR/$rel"
    [ -f "$FILE" ] || continue
    OUT=$(python3 "$RENDER" "$FILE" --summarize 2>&1)
    if [ $? -eq 0 ]; then
      HTML=$(printf '%s' "$OUT" | grep -oE '/[^ ]*PLAN\.html' | head -1)
      MESSAGES="${MESSAGES}${MESSAGES:+
}🖼️ PLAN.html auto-rendered: $HTML"
    else
      MESSAGES="${MESSAGES}${MESSAGES:+
}⚠️ PLAN.html render failed for $rel: $OUT"
    fi
  done <<EOF
$PATHS
EOF
fi

if [ "$STATUS" != "known" ]; then
  DIAG=$(printf '%s' "$NORMALIZED" | jq -r '.diagnostics | join(", ")' 2>/dev/null)
  MESSAGES="${MESSAGES}${MESSAGES:+
}render-plan-on-write: edit payload was only partially understood (${DIAG:-unparsed payload}); valid PLAN.md paths were processed."
fi
[ -z "$MESSAGES" ] || jq -cn --arg message "$MESSAGES" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$message}}'
exit 0
