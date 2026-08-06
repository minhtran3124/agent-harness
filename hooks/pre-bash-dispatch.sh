#!/bin/bash
# PreToolUse(Bash) dispatcher: one process for all git commit/push gates.
# Replays stdin into the existing hook scripts in settings order so contract
# tests and manual debug can still invoke each child directly.
# Non-commit/push commands exit 0 immediately after a single match.
# Exits 2 when a blocking child exits 2 or a required child/lib is missing.
# Deny JSON on child stdout is forwarded (permissionDecision).

INPUT=$(cat /dev/stdin)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPT_DIR/lib/git-command.sh" 2>/dev/null
command -v hook_cmd_is_git_commit_or_push >/dev/null 2>&1 || {
  echo "[PRE-BASH] git-command matcher lib missing — redeploy harness (blocking to fail safe)." >&2
  exit 2
}

COMMAND=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
hook_cmd_is_git_commit_or_push "$COMMAND" || exit 0

run_child() {
  local child="$1" out rc
  if [ ! -f "$SCRIPT_DIR/$child" ]; then
    echo "[PRE-BASH] missing child hook $child — redeploy harness (blocking to fail safe)." >&2
    exit 2
  fi
  out=$(printf '%s' "$INPUT" | bash "$SCRIPT_DIR/$child" 2>&1)
  rc=$?
  if [ -n "$out" ]; then
    printf '%s\n' "$out"
  fi
  if [ "$rc" -ne 0 ]; then
    exit "$rc"
  fi
  # Child may allow (exit 0) while emitting deny JSON — honor deny.
  if printf '%s' "$out" | grep -q '"permissionDecision":"deny"'; then
    exit 0
  fi
}

# Push: only untracked-py (matches prior per-hook early-exit behavior).
if command -v hook_cmd_is_git_commit >/dev/null 2>&1 && ! hook_cmd_is_git_commit "$COMMAND"; then
  run_child check-untracked-py.sh
  exit 0
fi

# Commit: same order as legacy settings.json Bash PreToolUse list.
run_child check-untracked-py.sh
run_child commit-quality-gate.sh
run_child risk-corroboration.sh
run_child branch-guard.sh
exit 0
