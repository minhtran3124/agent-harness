#!/bin/bash
# PreToolUse hook: block git commit/push if untracked .py files exist.
# Prevents CI failures from missing imports.

INPUT=$(cat)
CMD=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // ""')

# Only act on git commit/push (tokenizing matcher — resists cd/&&/-C/-c bypass)
source "$(cd "$(dirname "$0")" && pwd)/lib/git-command.sh" 2>/dev/null
# Fail closed: if the matcher lib is missing, block rather than let untracked .py slip through.
command -v hook_cmd_is_git_commit_or_push >/dev/null 2>&1 || {
  echo "[UNTRACKED-PY] git-command matcher lib missing — redeploy harness (blocking to fail safe)." >&2
  exit 2
}
hook_cmd_is_git_commit_or_push "$CMD" || exit 0

# Exclude the deployed harness itself. The anchor matters: `git ls-files` returns
# repo-relative paths, so a root-level deployment is `.claude/skills/...` with NO leading
# slash — a bare `/\.claude/` pattern misses it and denies every commit in a fresh consumer
# whose .gitignore does not yet list .claude/. Match both `.claude/…` and `app/.claude/…`.
FILES=$(git ls-files --others --exclude-standard 2>/dev/null | grep -E '\.py$' | grep -vE '(^|/)\.claude/')
if [ -n "$FILES" ]; then
  jq -cn --arg f "$FILES" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: ("Untracked .py not staged (would break CI imports):\n" + $f + "\n\nRun: git add <files> — or gitignore if intentional.")
    }
  }'
fi
