#!/bin/bash
# Contract tests for hooks/pr-opened.sh (reminder only) and hooks/clean-worktrees.sh (removes the
# worktree and branch of a branch whose PR is merged; never forces).
source "$(dirname "$0")/../lib.sh"

# ---- pr-opened.sh ----
R=$(new_repo pr-opened.sh)
t "pr-opened adds a review reminder after gh pr create and names the PR number"
run_hook "$R" pr-opened.sh '{"tool_input":{"command":"gh pr create --title x"},"tool_response":"https://github.com/o/r/pull/42"}'
if [ "$RC" = 0 ] && printf '%s' "$OUT" | jq -e '.hookSpecificOutput.additionalContext | test("#42")' >/dev/null; then pass; else fail "rc=$RC out=$OUT"; fi

t "pr-opened says nothing for another command"
run_hook "$R" pr-opened.sh '{"tool_input":{"command":"gh pr view 1"}}'
if [ "$RC" = 0 ] && [ -z "$OUT" ]; then pass; else fail "rc=$RC out=$OUT"; fi

# ---- clean-worktrees.sh ----
setup() {  # $1 = merged|open ; leaves $MAIN, $WT, $STUB
  MAIN=$(mktemp -d); _CLEANUP_DIRS+=("$MAIN")
  git -C "$MAIN" init -q -b main; git -C "$MAIN" config user.email t@t; git -C "$MAIN" config user.name t
  git -C "$MAIN" commit -q --allow-empty -m base
  WT="$MAIN-wt"; _CLEANUP_DIRS+=("$WT")
  git -C "$MAIN" worktree add -q -b feat "$WT"
  git -C "$WT" commit -q --allow-empty -m work
  mkdir -p "$MAIN/hooks"; cp "$ROOT/hooks/clean-worktrees.sh" "$MAIN/hooks/"
  STUB=$(mktemp -d); _CLEANUP_DIRS+=("$STUB")
  tip=$(git -C "$MAIN" rev-parse feat)
  if [ "$1" = merged ]; then printf '#!/bin/sh\necho %s\n' "$tip" > "$STUB/gh"; else printf '#!/bin/sh\nexit 0\n' > "$STUB/gh"; fi
  chmod +x "$STUB/gh"
}
run() { OUT=$(cd "$MAIN" && PATH="$STUB:$PATH" bash hooks/clean-worktrees.sh 2>&1); RC=$?; }

setup merged; git -C "$MAIN" merge -q --no-ff feat -m merge
t "merged PR: worktree and branch are removed"
run
if [ ! -d "$WT" ] && ! git -C "$MAIN" rev-parse -q --verify feat >/dev/null; then pass; else fail "rc=$RC out=$OUT"; fi

setup open
t "PR not merged: worktree and branch are kept"
run
if [ -d "$WT" ] && git -C "$MAIN" rev-parse -q --verify feat >/dev/null; then pass; else fail "out=$OUT"; fi

setup merged; git -C "$MAIN" merge -q --no-ff feat -m merge; echo dirty > "$WT/untracked.txt"; git -C "$WT" add untracked.txt
t "merged PR but uncommitted changes in the worktree: kept, nothing forced"
run
if [ -d "$WT" ] && [ -f "$WT/untracked.txt" ] && printf '%s' "$OUT" | grep -q 'kept'; then pass; else fail "out=$OUT"; fi

setup merged
t "merged on GitHub but not in git history (squash): worktree removed, branch kept with a note"
run
if [ ! -d "$WT" ] && git -C "$MAIN" rev-parse -q --verify feat >/dev/null && printf '%s' "$OUT" | grep -q 'kept branch feat'; then pass; else fail "out=$OUT"; fi

setup merged
t "PostToolUse mode ignores a command that is not a merge"
OUT=$(cd "$MAIN" && printf '{"tool_input":{"command":"ls"}}' | PATH="$STUB:$PATH" bash hooks/clean-worktrees.sh PostToolUse 2>&1)
if [ -d "$WT" ] && [ -z "$OUT" ]; then pass; else fail "out=$OUT"; fi

finish
