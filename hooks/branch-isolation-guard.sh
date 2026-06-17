#!/bin/bash
# PreToolUse hook (Write|Edit): hard-block a code edit when implementation is underway
# on a SHARED branch without an isolated worktree/feature branch.
#
# The gap this closes: branch creation in this harness is prompt-only. writing-plans
# does not invoke using-git-worktrees, and the execution skills' "Step 0" branch check
# is a soft instruction the model may skip. branch-guard.sh only WARNS, and only at
# commit time — after the work is already on the shared branch. This hook makes the
# "isolate before implementing" rule STRUCTURAL at write time.
#
# Fires (DENY) only when ALL hold — kept narrow on purpose so it never fights the
# harness's own development or the tiny lane:
#   1. current branch is a shared/protected branch (HARNESS_SHARED_BRANCHES,
#      default "main master") — keep this in sync with the execution skills' Step 0;
#   2. an active plan exists (a specs/*/PLAN.md with `status: active`) — i.e. an
#      implementation is in progress; tiny-lane edits (no plan) pass through;
#   3. the edited file is NOT under specs/ — plan/SUMMARY bookkeeping must stay writable.
#
# Break-glass: set BRANCH_ISOLATION_REASON="<why>" to allow the write; the override is
# appended to docs/harness-experimental/break-glass-log.md (override → audit trail).
# Mirrors protected-path-guard.sh's pattern.
set -u

INPUT=$(cat)
FILE=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""')
[ -z "$FILE" ] && exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
REL="${FILE#"$ROOT/"}"

# (3) plan/spec bookkeeping is always allowed.
case "$REL" in specs/*) exit 0 ;; esac

# (1) only act on a shared/protected branch.
BR=$(git -C "$ROOT" symbolic-ref --short HEAD 2>/dev/null)
[ -z "$BR" ] && exit 0   # detached HEAD / not a repo → don't interfere
SHARED="${HARNESS_SHARED_BRANCHES:-main master}"
on_shared=0
for s in $SHARED; do [ "$BR" = "$s" ] && on_shared=1 && break; done
[ "$on_shared" -eq 0 ] && exit 0   # on a feature branch / worktree → allow

# (2) only when an implementation is actually in progress (an active plan exists).
grep -rqsl --include='PLAN.md' '^status: active' "$ROOT/specs" 2>/dev/null || exit 0

REASON="${BRANCH_ISOLATION_REASON:-}"
if [ -n "$REASON" ]; then
  LOG="$ROOT/docs/harness-experimental/break-glass-log.md"
  mkdir -p "$(dirname "$LOG")" 2>/dev/null
  printf -- '- %s — branch-isolation `%s` on `%s` — %s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$REL" "$BR" "$REASON" >> "$LOG" 2>/dev/null || true
  echo "[BRANCH-ISOLATION] break-glass override for $REL on '$BR' (recorded to break-glass-log.md)" >&2
  exit 0
fi

jq -cn --arg b "$BR" --arg f "$REL" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: ("Implementation is underway (an active PLAN.md exists) but you are on shared branch " + $b + ".\nEditing " + $f + " here skips the feature-branch/worktree isolation step.\nFix: invoke the using-git-worktrees skill to create an isolated worktree + branch, then continue there.\nOverride after confirming: set BRANCH_ISOLATION_REASON=<why> (recorded to the break-glass log).")
  }
}'
