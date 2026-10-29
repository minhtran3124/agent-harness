#!/bin/bash
# Contract tests for hooks/pr-opened.sh (reminder only) and hooks/clean-worktrees.sh (removes the
# worktree and branch of a merged branch; forces only on an exact-tip merged PR).
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
t "merged on GitHub with the exact tip but not in git history (squash): worktree and branch are removed"
run
if [ ! -d "$WT" ] && ! git -C "$MAIN" rev-parse -q --verify feat >/dev/null && printf '%s' "$OUT" | grep -q 'removed feat'; then pass; else fail "out=$OUT"; fi

setup merged; git -C "$WT" commit -q --allow-empty -m after-merge
t "squash merge but one commit after the merge (tip differs from the PR head): worktree and branch are kept"
run
if [ -d "$WT" ] && git -C "$MAIN" rev-parse -q --verify feat >/dev/null; then pass; else fail "out=$OUT"; fi

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

for cmd in 'gh pr merge 7 --squash --delete-branch' 'cd x && gh pr merge 7' 'FOO=1 gh pr merge 7' 'gh pr merge https://github.com/o/r/pull/7' 'gh api repos/o/r/pulls/7/merge -X PUT' 'gh api repos/{owner}/{repo}/pulls/7/merge -X PUT' '{ gh pr merge 7; }' 'gh pr merge "7"' 'gh api "repos/o/r/pulls/7/merge" -X PUT' "gh pr merge '7' --squash" $'cat <<< "x"\ngh pr merge 7' $'echo a << b\ngh pr merge 7'; do
  setup2
  t "real merge cleans only PR 7's branch: $cmd"
  hook "$cmd"
  if [ ! -d "$WT" ] && [ -d "$WT2" ] && ! git -C "$MAIN" rev-parse -q --verify feat >/dev/null && git -C "$MAIN" rev-parse -q --verify feat2 >/dev/null; then pass; else fail "rc=$RC out=$OUT"; fi
done

setup2
t "chained merges clean the branch of every merged PR"
hook 'gh pr merge 7 && gh pr merge 8'
if [ ! -d "$WT" ] && [ ! -d "$WT2" ]; then pass; else fail "out=$OUT"; fi

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

# ---- clean-worktrees.sh #494: fetch, SessionStart sweep, worktree-* branches, no gh, config ----
REALGIT=$(command -v git)
NOGH=$(mktemp -d); _CLEANUP_DIRS+=("$NOGH")  # a PATH with the basic tools and no gh
for c in git bash sh jq awk sed grep tr cat pwd head sort uniq printf dirname basename env mkdir rm date cut wc; do
  p=$(command -v "$c" 2>/dev/null) && ln -sf "$p" "$NOGH/$c"
done
rsetup() {  # $MAIN with remote r1 (a bare repo), main pushed; $STUB is an empty dir
  MAIN=$(mktemp -d); REM=$(mktemp -d); STUB=$(mktemp -d); _CLEANUP_DIRS+=("$MAIN" "$REM" "$STUB")
  git init -q --bare -b main "$REM"
  git -C "$MAIN" init -q -b main; git -C "$MAIN" config user.email t@t; git -C "$MAIN" config user.name t
  git -C "$MAIN" commit -q --allow-empty -m base
  git -C "$MAIN" remote add r1 "$REM"; git -C "$MAIN" push -q r1 main; git -C "$MAIN" fetch -q r1
  mkdir -p "$MAIN/hooks"; cp "$ROOT/plugins/harness/hooks/clean-worktrees.sh" "$MAIN/hooks/"
}
# gone_branch <name>: merged into main, pushed with upstream, then deleted on the remote
gone_branch() {
  git -C "$MAIN" checkout -q -b "$1"; git -C "$MAIN" commit -q --allow-empty -m "w-$1"
  git -C "$MAIN" push -q -u r1 "$1" 2>/dev/null; git -C "$MAIN" checkout -q main
  git -C "$MAIN" merge -q --no-ff "$1" -m "m-$1"; git -C "$MAIN" push -q r1 main
  git -C "$REM" branch -q -D "$1"
}
ghstub() {  # <branch> <tip>: gh pr list --head <branch> returns <tip>
  printf '#!/bin/sh\ncase "$4" in %s) echo %s ;; esac\nexit 0\n' "$1" "$2" > "$STUB/gh"; chmod +x "$STUB/gh"
}
# rrun <mode> [VAR=value ...]: run in $MAIN (or $CWD) against remote r1; with NOGH=1 gh is absent
rrun() {
  local mode=$1; shift
  local path="$STUB:$PATH"; [ -n "${NOGH_RUN:-}" ] && path="$STUB:$NOGH"
  OUT=$(cd "${CWD:-$MAIN}" && env CLEAN_REMOTE=r1 "$@" PATH="$path" bash "$MAIN/hooks/clean-worktrees.sh" $mode </dev/null 2>&1); RC=$?
}
has() { git -C "$MAIN" rev-parse -q --verify "refs/heads/$1" >/dev/null; }

# item 1: fetch --prune
rsetup; gone_branch feat; NOGH_RUN=1
t "item 1: fetch --prune makes a branch the remote deleted visible (removed without gh)"
rrun ""
if ! has feat; then pass; else fail "out=$OUT"; fi
unset NOGH_RUN

rsetup; git -C "$MAIN" checkout -q -b feat; git -C "$MAIN" commit -q --allow-empty -m w; git -C "$MAIN" checkout -q main
git -C "$MAIN" merge -q feat; ghstub feat "$(git -C "$MAIN" rev-parse feat)"
t "item 1: an unreachable remote does not stop the script; other cleanup still happens"
rrun "" CLEAN_REMOTE=/nonexistent/remote.git
if [ "$RC" = 0 ] && ! has feat; then pass; else fail "rc=$RC out=$OUT"; fi

# item 2: SessionStart sweep
rsetup; git -C "$MAIN" checkout -q -b old; git -C "$MAIN" commit -q --allow-empty -m w; git -C "$MAIN" checkout -q main
git -C "$MAIN" merge -q --no-ff old -m m
SWT="$MAIN-session"; _CLEANUP_DIRS+=("$SWT"); git -C "$MAIN" worktree add -q -b cur "$SWT"
printf '#!/bin/sh\ncase "$4" in old) echo %s ;; cur) echo %s ;; esac\n' "$(git -C "$MAIN" rev-parse old)" "$(git -C "$SWT" rev-parse cur)" > "$STUB/gh"; chmod +x "$STUB/gh"
t "item 2: SessionStart returns valid additionalContext JSON, removes merged branches, keeps the session's branch and worktree"
CWD=$SWT rrun SessionStart; unset CWD
if [ "$(printf '%s' "$OUT" | jq -r .hookSpecificOutput.hookEventName)" = SessionStart ] && printf '%s' "$OUT" | jq -r .hookSpecificOutput.additionalContext | grep -q 'removed old' \
   && ! has old && has cur && [ -d "$SWT" ]; then pass; else fail "rc=$RC out=$OUT"; fi

t "item 2: a SessionStart sweep stops at its time budget between branches and says so"
rsetup
for bn in b1 b2; do git -C "$MAIN" checkout -q -b $bn; git -C "$MAIN" commit -q --allow-empty -m w-$bn; git -C "$MAIN" checkout -q main; git -C "$MAIN" merge -q --no-ff $bn -m m-$bn; done
printf '#!/bin/sh\nsleep 4\ncase "$4" in b1) echo %s ;; b2) echo %s ;; esac\n' "$(git -C "$MAIN" rev-parse b1)" "$(git -C "$MAIN" rev-parse b2)" > "$STUB/gh"; chmod +x "$STUB/gh"
rrun SessionStart CLEAN_BUDGET=3
if [ "$RC" = 0 ] && printf '%s' "$OUT" | jq -r .hookSpecificOutput.additionalContext | grep -q 'stopped: time budget' && { has b1 && ! has b2 || has b2 && ! has b1; }; then pass; else fail "rc=$RC out=$OUT"; fi

t "item 2: SessionStart keeps a merged worktree that another live process uses, and removes it once the process is gone"
rsetup; git -C "$MAIN" checkout -q -b old2; git -C "$MAIN" commit -q --allow-empty -m w; git -C "$MAIN" checkout -q main
git -C "$MAIN" merge -q --no-ff old2 -m m2
OWT="$MAIN-other"; _CLEANUP_DIRS+=("$OWT"); git -C "$MAIN" worktree add -q "$OWT" old2
ghstub old2 "$(git -C "$MAIN" rev-parse old2)"
(cd "$OWT" && exec sleep 60) & LIVEPID=$!
sleep 1
rrun SessionStart; OUT1=$OUT
KEPT=""; if has old2 && [ -d "$OWT" ]; then KEPT=1; fi
kill "$LIVEPID" 2>/dev/null; wait "$LIVEPID" 2>/dev/null
rrun SessionStart
if [ -n "$KEPT" ] && ! has old2 && [ ! -d "$OWT" ]; then pass; else fail "kept=$KEPT out1=$OUT1 out2=$OUT"; fi

t "item 2: hooks.json runs clean-worktrees.sh SessionStart beside session-rules.sh"
if jq -e '[.hooks.SessionStart[].hooks[].args | join(" ")] | (map(test("session-rules.sh")) | any) and (map(test("clean-worktrees.sh SessionStart$")) | any)' "$ROOT/plugins/harness/hooks/hooks.json" >/dev/null; then pass; else fail "hooks.json"; fi
t "item 2: the SessionStart sweep has a timeout and runs only on startup, and session-rules.sh has no matcher"
if jq -e '([.hooks.SessionStart[] | select(.hooks[].args | join(" ") | test("clean-worktrees.sh SessionStart$"))] | length == 1 and (.[0].matcher == "startup") and (.[0].hooks[0].timeout | type == "number" and . > 0 and . <= 60)) and ([.hooks.SessionStart[] | select(.hooks[].args | join(" ") | test("session-rules.sh"))] | .[0].matcher == null)' "$ROOT/plugins/harness/hooks/hooks.json" >/dev/null; then pass; else fail "hooks.json timeout/matcher"; fi

# item 3: worktree-* agent branches
rsetup
for n in a b c; do git -C "$MAIN" checkout -q -b "worktree-$n" main; git -C "$MAIN" commit -q --allow-empty -m "w$n"; done
git -C "$MAIN" checkout -q main
git -C "$MAIN" push -q r1 worktree-a:refs/heads/other worktree-b:refs/heads/other2
BWT="$MAIN-b"; _CLEANUP_DIRS+=("$BWT"); git -C "$MAIN" worktree add -q "$BWT" worktree-b
git -C "$MAIN" fetch -q r1
# r1/HEAD alone does not count: worktree-d is reachable only through a r1/HEAD ref
git -C "$MAIN" checkout -q -b worktree-d main; git -C "$MAIN" commit -q --allow-empty -m wd; git -C "$MAIN" checkout -q main
git -C "$MAIN" push -q r1 worktree-d:refs/heads/HEAD; git -C "$MAIN" fetch -q r1
NOGH_RUN=1
t "item 3: worktree-* not checked out and contained in a remote branch is removed; others are kept"
rrun ""
if ! has worktree-a && has worktree-b && has worktree-c && has worktree-d && [ -d "$BWT" ]; then pass; else fail "out=$OUT a=$(has worktree-a && echo y) b=$(has worktree-b && echo y) c=$(has worktree-c && echo y) d=$(has worktree-d && echo y)"; fi
unset NOGH_RUN

# item 3: a failed fetch leaves remote-tracking refs stale, so the worktree-* rule must not run
rsetup
git -C "$MAIN" checkout -q -b worktree-s main; git -C "$MAIN" commit -q --allow-empty -m ws; git -C "$MAIN" checkout -q main
git -C "$MAIN" push -q r1 worktree-s:refs/heads/other; git -C "$MAIN" fetch -q r1
git -C "$REM" branch -q -D other
printf '#!/bin/sh\n[ "$1" = fetch ] && exit 1\nexec %s "$@"\n' "$REALGIT" > "$STUB/git"; chmod +x "$STUB/git"
NOGH_RUN=1
t "item 3: worktree-* is kept when git fetch fails (stale remote-tracking refs)"
rrun ""
if has worktree-s; then pass; else fail "out=$OUT"; fi
unset NOGH_RUN

# item 5: no gh
rsetup; gone_branch feat; git -C "$MAIN" checkout -q -b kept1; git -C "$MAIN" commit -q --allow-empty -m k; git -C "$MAIN" push -q -u r1 kept1 2>/dev/null; git -C "$MAIN" checkout -q main
NOGH_RUN=1
t "item 5: no gh: upstream gone and tip in <remote>/main is removed; upstream present is kept"
rrun ""
if ! has feat && has kept1; then pass; else fail "out=$OUT"; fi

rsetup; gone_branch feat; git -C "$REM" update-ref -d refs/heads/main
t "item 5: no gh and <remote>/main missing: no rule applies, branch kept"
rrun ""
if has feat; then pass; else fail "out=$OUT"; fi
unset NOGH_RUN

# item 6: CLEAN_KEEP
rsetup; git -C "$MAIN" checkout -q -b automation; git -C "$MAIN" commit -q --allow-empty -m w; git -C "$MAIN" checkout -q main
git -C "$MAIN" merge -q --no-ff automation -m m; ghstub automation "$(git -C "$MAIN" rev-parse automation)"
t "item 6: CLEAN_KEEP=\"automation workflow\" leaves a merged branch named automation"
rrun "" CLEAN_KEEP="automation workflow"
if has automation; then pass; else fail "out=$OUT"; fi
t "item 6: without CLEAN_KEEP the same merged branch is removed"
rrun ""
if ! has automation; then pass; else fail "out=$OUT"; fi

# long-lived branches are never removed, even with a merged PR at the exact tip
for lb in develop release/1.0; do
  rsetup; git -C "$MAIN" checkout -q -b "$lb"; git -C "$MAIN" commit -q --allow-empty -m w; git -C "$MAIN" checkout -q main
  git -C "$MAIN" merge -q --no-ff "$lb" -m m; ghstub "$lb" "$(git -C "$MAIN" rev-parse "$lb")"
  t "long-lived branch $lb is kept despite a merged PR at its tip"
  rrun ""
  if has "$lb"; then pass; else fail "out=$OUT"; fi
done

# item 7: CLEAN_STRICT
rsetup; gone_branch run/1; NOGH_RUN=1
t "item 7: a CLEAN_STRICT branch is not removed by the upstream-gone rule (no gh)"
rrun "" CLEAN_STRICT="run/*"
if has run/1; then pass; else fail "out=$OUT"; fi
unset NOGH_RUN
ghstub run/1 "$(git -C "$MAIN" rev-parse run/1)"
t "item 7: a CLEAN_STRICT branch is removed when a merged PR has its exact tip"
rrun "" CLEAN_STRICT="run/*"
if ! has run/1; then pass; else fail "out=$OUT"; fi

# no force delete outside the exact-tip merged-PR rule: when `git branch -d` refuses, the branch is kept
rsetup; gone_branch feat; git -C "$MAIN" checkout -q -b worktree-w main; git -C "$MAIN" commit -q --allow-empty -m ww; git -C "$MAIN" push -q r1 worktree-w:refs/heads/other; git -C "$MAIN" fetch -q r1; git -C "$MAIN" checkout -q main
REALGIT=$(command -v git)
printf '#!/bin/sh\ncase "$*" in *"branch -d"*|*"branch -q --set-upstream-to"*) exit 1 ;; esac\nexec %s "$@"\n' "$REALGIT" > "$STUB/git"; chmod +x "$STUB/git"
NOGH_RUN=1
t "no force delete: when git branch -d refuses, the upstream-gone and worktree-* rules keep the branch"
rrun ""
if has feat && has worktree-w; then pass; else fail "out=$OUT"; fi
unset NOGH_RUN

# item 8: CLEAN_RECREATE
rsetup
t "item 8: CLEAN_RECREATE pushes <remote>/main when the branch is missing on the remote"
rrun "" CLEAN_RECREATE="automation"
if [ "$(git -C "$REM" rev-parse -q --verify refs/heads/automation)" = "$(git -C "$REM" rev-parse refs/heads/main)" ]; then pass; else fail "out=$OUT"; fi

rsetup; git -C "$MAIN" checkout -q -b automation; git -C "$MAIN" commit -q --allow-empty -m a; git -C "$MAIN" push -q r1 automation; git -C "$MAIN" checkout -q main
before=$(git -C "$REM" rev-parse refs/heads/automation)
t "item 8: no push when the branch already exists on the remote"
rrun "" CLEAN_RECREATE="automation"
if [ "$(git -C "$REM" rev-parse refs/heads/automation)" = "$before" ]; then pass; else fail "out=$OUT"; fi

rsetup
printf '#!/bin/sh\n[ "$1" = ls-remote ] && exit 128\nexec %s "$@"\n' "$REALGIT" > "$STUB/git"; chmod +x "$STUB/git"
t "item 8: no push when ls-remote fails for another reason than a missing branch"
rrun "" CLEAN_RECREATE="automation"
if ! git -C "$REM" rev-parse -q --verify refs/heads/automation >/dev/null; then pass; else fail "out=$OUT"; fi

rsetup
t "item 8: CLEAN_RECREATE ignores an unsafe branch name (leading dash)"
rrun "" CLEAN_RECREATE="-f"
if ! git -C "$REM" rev-parse -q --verify refs/heads/-f >/dev/null; then pass; else fail "out=$OUT"; fi

# docs: the SessionStart bullet in docs/hooks.md reads as whole sentences
DOCS_HOOKS="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/docs/hooks.md"
t "docs/hooks.md: no sentence is cut by 'cleaned It is registered'"
if ! grep -q 'cleaned It is' "$DOCS_HOOKS"; then pass; else fail "garbled sentence in docs/hooks.md"; fi

t "docs: skills README ties the live-process skip to the SessionStart sweep only"
README_ROW=$(grep 'removes merged worktrees and branches after a merge' "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/plugins/harness/skills/README.md")
if printf '%s' "$README_ROW" | grep -q 'session-start sweep also skips a worktree another live process uses' && ! printf '%s' "$README_ROW" | grep -q 'and a worktree another live process uses'; then pass; else fail "row=$README_ROW"; fi

finish

t "docs: CLAUDE.md hook row ties the live-process skip to the SessionStart sweep only"
ROW=$(grep '^| `clean-worktrees.sh`' "$ROOT/CLAUDE.md")
if printf '%s' "$ROW" | grep -q 'session-start sweep also skips a worktree a live process uses' && ! printf '%s' "$ROW" | grep -q 'protected names ([^)]*) and a worktree a live process uses'; then pass; else fail "row=$ROW"; fi
