#!/bin/bash
# PreToolUse hook: warn (never block) when committing directly on main/master.
#
# A commit straight onto the default branch sidesteps the feature-branch /
# worktree workflow (see skills/using-git-worktrees). This hook only nudges:
# it prints a warning to stderr and exits 0 — it NEVER blocks the commit.
#
# Only acts on `git commit`. Bash 3.2 compatible (no declare -A, no grep -P).

INPUT=$(cat /dev/stdin)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Only act on git commit (tokenizing matcher — resists cd/&&/-C/-c bypass)
source "$(cd "$(dirname "$0")" && pwd)/lib/git-command.sh" 2>/dev/null
# Warn-only hook: if the matcher lib is missing, stay silent and never block.
command -v hook_cmd_is_git_commit >/dev/null 2>&1 || exit 0
hook_cmd_is_git_commit "$COMMAND" || exit 0

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Repo root: runtime answer first, git-from-CWD second. NEVER from SCRIPT_DIR — see
# specs/fix-hook-project-root-resolution (silent wrong-repo resolution with exit 0).
REPO_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
if [ -z "$REPO_DIR" ]; then
  echo "[branch-guard] project root unknown — branch check skipped." >&2
  exit 0
fi
cd "$REPO_DIR" || exit 0

BR=$(git symbolic-ref --short HEAD 2>/dev/null)

if [ "$BR" = "main" ] || [ "$BR" = "master" ]; then
  echo "[BRANCH GUARD] You are about to commit on '$BR'. Prefer a feature branch or a git worktree (see skills/using-git-worktrees)." >&2
fi

exit 0
