#!/bin/bash
# PreToolUse hook (Write|Edit): hard-block a code edit on a SHARED branch. EVERY lane —
# tiny, normal, high-risk — must cut a branch before implementing.
#
# The gap this closes: branch creation in this harness is prompt-only. writing-plans
# does not invoke using-git-worktrees, and the execution skills' "Step 0" branch check
# is a soft instruction the model may skip. branch-guard.sh only WARNS, and only at
# commit time — after the work is already on the shared branch. This hook makes the
# "branch before implementing" rule STRUCTURAL at write time.
#
# Fires (DENY) when BOTH hold:
#   1. current branch is a shared/protected branch (HARNESS_SHARED_BRANCHES,
#      default "main master") — keep this in sync with the execution skills' Step 0;
#   2. the edited file is NOT under specs/ — plan/SUMMARY bookkeeping must stay writable
#      (intake has to be able to write SUMMARY.md *before* the branch exists).
#
# NOTE — no lane exemption. This hook previously also required an active PLAN.md, which
# let the tiny lane (no plan by definition) write straight to main. That was the whole
# hole: "branch per lane" is a rule about *where you write*, not about *how much
# ceremony the task earned*. A one-line typo fix on main is still a commit on main.
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
[ "$on_shared" -eq 0 ] && exit 0   # on a task branch / worktree → allow

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
    permissionDecisionReason: ("You are on shared branch " + $b + ". Every lane — tiny, normal and high-risk — cuts a branch BEFORE implementing, so editing " + $f + " here is not allowed.\nFix (tiny lane): git checkout -b <type>/<slug>, then re-apply the edit.\nFix (normal / high-risk): invoke the using-git-worktrees skill for an isolated worktree + branch, then continue there.\nspecs/ bookkeeping (SUMMARY.md, PLAN.md) stays writable here — only implementation is blocked.\nOverride after confirming: set BRANCH_ISOLATION_REASON=<why> (recorded to the break-glass log).")
  }
}'
