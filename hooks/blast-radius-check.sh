#!/bin/bash
# PostToolUse(Edit|Write): flag edits to files outside the active PLAN.md <files> set.
#
# Catches in-flight scope creep (a wave touching files it never declared). Default is
# WARN (non-blocking additionalContext). BLAST_RADIUS_STRICT=1 makes it exit 2 so the
# model must address the violation.
#
# No-op (silent) when: no active PLAN.md exists, the plan declares no <files>, or the
# edited file is bookkeeping (specs/, docs/, *.md). This keeps it quiet outside of
# active plan execution. Exits 0 unless STRICT + out-of-scope.

INPUT=$(cat /dev/stdin)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Repo root: runtime answer first, git-from-CWD second. NEVER from SCRIPT_DIR — a hook installed
# outside the project whose own dir sits inside ANY git repo resolves to THAT repo with exit 0
# (specs/fix-hook-project-root-resolution). SCRIPT_DIR stays, but only to locate this hook's libs.
REPO_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
if [ -z "$REPO_DIR" ]; then
  echo "[blast-radius] project root unknown (CLAUDE_PROJECT_DIR unset, CWD not a git work tree) — plan-scope check skipped." >&2
  exit 0
fi
source "$SCRIPT_DIR/lib/lane.sh" 2>/dev/null
REPO_DIR="$(cd "$REPO_DIR" 2>/dev/null && pwd -P)"
NORMALIZER="$SCRIPT_DIR/lib/normalize-tool-input.py"
if command -v python3 >/dev/null 2>&1 && [ -f "$NORMALIZER" ]; then
  NORMALIZED=$(printf '%s' "$INPUT" | python3 "$NORMALIZER" --root "$REPO_DIR" 2>/dev/null)
else
  NORMALIZED='{"status":"unknown","paths":[],"diagnostics":["normalizer-unavailable"]}'
fi
STATUS=$(printf '%s' "$NORMALIZED" | jq -r '.status // "unknown"' 2>/dev/null)
PATHS=$(printf '%s' "$NORMALIZED" | jq -r '.paths[]?' 2>/dev/null)
MESSAGES=""
if [ "$STATUS" != "known" ]; then
  DIAG=$(printf '%s' "$NORMALIZED" | jq -r '.diagnostics | join(", ")' 2>/dev/null)
  MESSAGES="blast-radius: edit payload was only partially understood (${DIAG:-unparsed payload}); valid paths were checked, but scope coverage is incomplete."
fi

# Find the active PLAN.md. `status: active` is the ONLY thing that arms this hook — there is
# deliberately no "else most recent" fallback. A shipped plan's <files> set is a record of what
# that work touched, not a scope constraint on everything that comes after it; falling back to it
# made every long-finished plan police every future edit, forever.
# hooks/lib/lane.sh (shared with risk-corroboration.sh's Lane fallback). A missing lib
# fails OPEN here (command -v guard), consistent with this hook's own default: no
# active-plan signal available → no scope to creep out of.
if command -v hook_lib_find_active_plan >/dev/null 2>&1; then
  PLAN=$(hook_lib_find_active_plan "$REPO_DIR") || PLAN=""
else
  PLAN=""
fi
if [ -z "$PLAN" ]; then
  [ -z "$MESSAGES" ] || jq -cn --arg message "$MESSAGES" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$message}}'
  exit 0
fi

# Declared files: <files>...</files> tags (XML syntax) plus `- **Files:** ...`
# field bullets (markdown syntax, rules/plan-format.md "Task Schema — two
# syntaxes"). Both comma-separated; union of the two sets. Fenced examples may
# leak into the set — harmless for an advisory allowlist (extra entries only).
DECLARED_XML=$(grep -oE '<files>[^<]*</files>' "$PLAN" 2>/dev/null \
  | sed -E 's#</?files>##g')
DECLARED_MD=$(grep -iE '^[-*][[:space:]]+\*\*Files(:\*\*|\*\*:)' "$PLAN" 2>/dev/null \
  | sed -E 's/^[-*][[:space:]]+\*\*[Ff]iles(:\*\*|\*\*:)[[:space:]]*//')
DECLARED=$(printf '%s\n%s\n' "$DECLARED_XML" "$DECLARED_MD" \
  | tr ',' '\n' | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' | grep -v '^$')
[ -z "$DECLARED" ] && {
  [ -z "$MESSAGES" ] || jq -cn --arg message "$MESSAGES" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$message}}'
  exit 0
}

OUTSIDE=""
while IFS= read -r REL; do
  [ -n "$REL" ] || continue
  case "$REL" in specs/*|docs/*|*.md) continue ;; esac
  INSCOPE=0
  bREL=$(basename "$REL")
  while IFS= read -r d; do
    [ -z "$d" ] && continue
    [ "$REL" = "$d" ] && INSCOPE=1 && break
    case "$REL" in */"$d") INSCOPE=1; break ;; esac
    [ "$bREL" = "$(basename "$d")" ] && INSCOPE=1 && break
  done <<EOF
$DECLARED
EOF
  if [ "$INSCOPE" -eq 0 ]; then
    OUTSIDE="${OUTSIDE}${OUTSIDE:+
}$REL"
  fi
done <<EOF
$PATHS
EOF

if [ -n "$OUTSIDE" ] && [ "$STATUS" = "known" ] && [ "${BLAST_RADIUS_STRICT:-0}" = "1" ]; then
  echo "[BLAST RADIUS] Paths outside the active plan's <files> set (${PLAN#"$REPO_DIR"/}):" >&2
  printf '%s\n' "$OUTSIDE" >&2
  echo "  Scope creep — escalate, or add the files to the plan." >&2
  exit 2
fi
if [ -n "$OUTSIDE" ]; then
  OUTSIDE_DISPLAY=$(printf '%s\n' "$OUTSIDE" | paste -sd ',' -)
  MESSAGES="${MESSAGES}${MESSAGES:+
}blast-radius: edited path(s) $OUTSIDE_DISPLAY which are NOT in the active plan <files> set (${PLAN#"$REPO_DIR"/}). If intentional, add them to the plan; otherwise treat as scope creep and consider escalating per rules/orchestration.md."
fi
[ -z "$MESSAGES" ] || jq -cn --arg message "$MESSAGES" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$message}}'
exit 0
