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
set -u

INPUT=$(cat)
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NORMALIZER="$SCRIPT_DIR/lib/normalize-tool-input.py"
if command -v python3 >/dev/null 2>&1 && [ -f "$NORMALIZER" ]; then
  NORMALIZED=$(printf '%s' "$INPUT" | python3 "$NORMALIZER" --root "$ROOT" 2>/dev/null)
else
  NORMALIZED='{"status":"unknown","paths":[],"diagnostics":["normalizer-unavailable"]}'
fi
STATUS=$(printf '%s' "$NORMALIZED" | jq -r '.status // "unknown"' 2>/dev/null)
TOOL_CLASS=$(printf '%s' "$NORMALIZED" | jq -r '.tool_class // "unknown"' 2>/dev/null)
PATHS=$(printf '%s' "$NORMALIZED" | jq -r '.paths[]?' 2>/dev/null)

# (1) only act on a shared/protected branch.
BR=$(git -C "$ROOT" symbolic-ref --short HEAD 2>/dev/null)
[ -z "$BR" ] && exit 0   # detached HEAD / not a repo → don't interfere
SHARED="${HARNESS_SHARED_BRANCHES:-main master}"
on_shared=0
for s in $SHARED; do [ "$BR" = "$s" ] && on_shared=1 && break; done
[ "$on_shared" -eq 0 ] && exit 0   # on a task branch / worktree → allow

REL=$(printf '%s\n' "$PATHS" | paste -sd ',' -)
[ -n "$REL" ] || REL="unparsed-edit-payload"
REASON="${BRANCH_ISOLATION_REASON:-}"
if [ -n "$REASON" ]; then
  LOG="$ROOT/docs/harness-experimental/break-glass-log.md"
  mkdir -p "$(dirname "$LOG")" 2>/dev/null
  printf -- '- %s — branch-isolation `%s` on `%s` — %s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$REL" "$BR" "$REASON" >> "$LOG" 2>/dev/null || true
  echo "[BRANCH-ISOLATION] break-glass override for $REL on '$BR' (recorded to break-glass-log.md)" >&2
  exit 0
fi

# On a shared branch, only a fully-known all-specs edit may pass. A mixed specs/code
# patch is implementation, and partial/unknown input must not become an empty allow.
#
# tool_class is checked as well as status: this hook is registered on the Write|Edit
# matcher, so a payload classified as anything but `edit` is a contradiction — the
# normalizer could not tell what it was looking at. A `known` shell classification with
# an empty path set would otherwise fall through the `[ -z "$PATHS" ]` allow below and
# let an edit through on a shared branch (the exact fail-open Task 4.2 exists to close).
if [ "$STATUS" != "known" ] || [ "$TOOL_CLASS" != "edit" ]; then
  DIAG=$(printf '%s' "$NORMALIZED" | jq -r '.diagnostics | join(", ")' 2>/dev/null)
  jq -cn --arg b "$BR" --arg c "tool_class=$TOOL_CLASS" --arg d "${DIAG:-unparsed payload}" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("Branch isolation could not safely classify the edit payload on shared branch " + $b + " (" + $c + "; " + $d + "). Re-run the edit after updating/redeploying the harness normalizer, or use the audited BRANCH_ISOLATION_REASON override.")
    }
  }'
  exit 0
fi

[ -z "$PATHS" ] && exit 0
ONLY_SPECS=1
while IFS= read -r rel; do
  case "$rel" in specs/*) ;; *) ONLY_SPECS=0 ;; esac
done <<EOF
$PATHS
EOF
[ "$ONLY_SPECS" -eq 1 ] && exit 0

jq -cn --arg b "$BR" --arg f "$REL" '{
  hookSpecificOutput: {
    hookEventName: "PreToolUse",
    permissionDecision: "deny",
    permissionDecisionReason: ("You are on shared branch " + $b + ". Every lane — tiny, normal and high-risk — cuts a branch BEFORE implementing, so editing " + $f + " here is not allowed.\nFix (tiny lane): git checkout -b <type>/<slug>, then re-apply the edit.\nFix (normal / high-risk): invoke the using-git-worktrees skill for an isolated worktree + branch, then continue there.\nspecs/ bookkeeping (SUMMARY.md, PLAN.md) stays writable here only when every touched path is under specs/.\nOverride after confirming: set BRANCH_ISOLATION_REASON=<why> (recorded to the break-glass log).")
  }
}'
