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
  mkdir -p "$MAIN/hooks"; cp "$ROOT/plugins/harness/hooks/clean-worktrees.sh" "$MAIN/hooks/"
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

# ---- clean-worktrees.sh PostToolUse: real merge command only, scoped to that PR's branch ----
# Two merged branches: feat (PR 7) and feat2 (PR 8). The gh stub logs every call to $STUB/calls.
setup2() {  # leaves $MAIN, $WT, $WT2, $STUB; the stub answers pr view <n>, pr view (current = PR 7) and pr list
  MAIN=$(mktemp -d); _CLEANUP_DIRS+=("$MAIN")
  git -C "$MAIN" init -q -b main; git -C "$MAIN" config user.email t@t; git -C "$MAIN" config user.name t
  git -C "$MAIN" commit -q --allow-empty -m base
  WT="$MAIN-wt"; WT2="$MAIN-wt2"; _CLEANUP_DIRS+=("$WT" "$WT2")
  git -C "$MAIN" worktree add -q -b feat "$WT"; git -C "$WT" commit -q --allow-empty -m work
  git -C "$MAIN" worktree add -q -b feat2 "$WT2"; git -C "$WT2" commit -q --allow-empty -m work2
  git -C "$MAIN" merge -q --no-ff feat -m m1; git -C "$MAIN" merge -q --no-ff feat2 -m m2
  mkdir -p "$MAIN/hooks"; cp "$ROOT/plugins/harness/hooks/clean-worktrees.sh" "$MAIN/hooks/"
  STUB=$(mktemp -d); _CLEANUP_DIRS+=("$STUB")
  tip1=$(git -C "$MAIN" rev-parse feat); tip2=$(git -C "$MAIN" rev-parse feat2)
  cat > "$STUB/gh" <<STUBEOF
#!/bin/sh
echo "\$*" >> "$STUB/calls"
case "\$1 \$2" in
  "pr view")
    [ -f "$STUB/fail" ] && exit 1
    case "\$3" in
      7|--json) echo '{"state":"MERGED","headRefName":"feat"}' ;;
      8) echo '{"state":"MERGED","headRefName":"feat2"}' ;;
      9) echo '{"state":"OPEN","headRefName":"feat2"}' ;;
      *) exit 1 ;;
    esac ;;
  "pr list") case "\$4" in feat) echo $tip1 ;; feat2) echo $tip2 ;; esac ;;
esac
exit 0
STUBEOF
  chmod +x "$STUB/gh"
}
hook() { OUT=$(cd "$MAIN" && printf '%s' "$(jq -n --arg c "$1" '{tool_input:{command:$c}}')" | PATH="$STUB:$PATH" bash hooks/clean-worktrees.sh PostToolUse 2>&1); RC=$?; }
nothing_removed() { [ -d "$WT" ] && [ -d "$WT2" ] && [ -z "$OUT" ] && [ ! -f "$STUB/calls" ]; }

for cmd in $'gh issue create -F - <<EOF\nplease run gh pr merge 7 later\nEOF' \
           'git commit -m "docs: gh pr merge 7 now cleans"' \
           "echo 'gh pr merge 7'" \
           'echo gh pr merge 7' \
           $'git commit -m "first\ngh pr merge 7\nlast"'; do
  setup2
  t "text that only mentions the merge phrase cleans nothing and calls no gh: ${cmd%%$'\n'*}"
  hook "$cmd"
  if nothing_removed; then pass; else fail "rc=$RC out=$OUT calls=$(cat "$STUB/calls" 2>/dev/null)"; fi
done

for cmd in 'gh pr merge 7 --squash --delete-branch' 'cd x && gh pr merge 7' 'FOO=1 gh pr merge 7' 'gh pr merge https://github.com/o/r/pull/7' 'gh api repos/o/r/pulls/7/merge -X PUT' 'gh api repos/{owner}/{repo}/pulls/7/merge -X PUT' '{ gh pr merge 7; }'; do
  setup2
  t "real merge cleans only PR 7's branch: $cmd"
  hook "$cmd"
  if [ ! -d "$WT" ] && [ -d "$WT2" ] && ! git -C "$MAIN" rev-parse -q --verify feat >/dev/null && git -C "$MAIN" rev-parse -q --verify feat2 >/dev/null; then pass; else fail "rc=$RC out=$OUT"; fi
done

setup2
t "merge without a number uses the PR of the current branch"
hook 'gh pr merge --squash'
if [ ! -d "$WT" ] && [ -d "$WT2" ] && grep -q '^pr view --json' "$STUB/calls"; then pass; else fail "out=$OUT calls=$(cat "$STUB/calls")"; fi

setup2; touch "$STUB/fail"
t "gh pr view fails: exit 0, no output, nothing removed"
hook 'gh pr merge 7'
if [ "$RC" = 0 ] && [ -z "$OUT" ] && [ -d "$WT" ] && [ -d "$WT2" ]; then pass; else fail "rc=$RC out=$OUT"; fi

setup2; rm -f "$STUB/fail"
t "PR from the command is not merged: nothing removed"
hook 'gh pr merge 9'
if [ "$RC" = 0 ] && [ -z "$OUT" ] && [ -d "$WT" ] && [ -d "$WT2" ]; then pass; else fail "rc=$RC out=$OUT"; fi

setup2
t "manual run with no argument still sweeps every merged branch"
OUT=$(cd "$MAIN" && PATH="$STUB:$PATH" bash hooks/clean-worktrees.sh 2>&1); RC=$?
if [ ! -d "$WT" ] && [ ! -d "$WT2" ]; then pass; else fail "out=$OUT"; fi

finish
