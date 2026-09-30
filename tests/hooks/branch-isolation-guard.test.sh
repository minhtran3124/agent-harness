#!/bin/bash
# Contract tests for hooks/branch-isolation-guard.sh — hard-block code edits on a shared
# branch, for EVERY lane, with a break-glass override.
#
# The lane-independence is the point: the hook used to also require an active PLAN.md,
# which let the tiny lane (no plan by definition) write straight to main. The first two
# cases below pin that hole shut — a tiny-lane edit with no plan anywhere must still be
# denied on a shared branch.
source "$(dirname "$0")/../lib.sh"

H=branch-isolation-guard.sh

# active_plan <repo> — drop a specs/<slug>/PLAN.md with status: active into the repo
active_plan() {
  mkdir -p "$1/specs/demo"
  printf -- '---\nslug: demo\nstatus: active\n---\n# Demo\n' > "$1/specs/demo/PLAN.md"
}

codex_patch() {
  jq -cn --arg command "$1" '{turn_id:"turn-redacted",hook_event_name:"PreToolUse",tool_name:"apply_patch",tool_input:{command:$command}}'
}

t "TINY LANE (no plan at all) on main → DENY (this is the hole that was open)"
repo=$(new_repo $H)   # new_repo inits on 'main'
run_hook "$repo" $H "$(json_file "$repo/app/x.py")"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "tiny lane on a task branch → allow (a branch exists; that is all the rule asks)"
repo=$(new_repo $H)
git -C "$repo" checkout -q -b fix/typo
run_hook "$repo" $H "$(json_file "$repo/app/x.py")"
assert_silent_ok

t "on main + active plan + code file → DENY"
repo=$(new_repo $H); active_plan "$repo"
run_hook "$repo" $H "$(json_file "$repo/app/x.py")"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "on main + specs/ bookkeeping file → allow (intake writes SUMMARY.md before the branch exists)"
repo=$(new_repo $H); active_plan "$repo"
run_hook "$repo" $H "$(json_file "$repo/specs/demo/PLAN.md")"
assert_silent_ok

t "on main + specs/ file + NO plan → allow (tiny-lane intake must still be able to write SUMMARY.md)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file "$repo/specs/demo/SUMMARY.md")"
assert_silent_ok

t "on a feature branch + active plan → allow (isolated)"
repo=$(new_repo $H); active_plan "$repo"
git -C "$repo" checkout -q -b feature/x
run_hook "$repo" $H "$(json_file "$repo/app/x.py")"
assert_silent_ok

t "break-glass reason → allow + audit note on stderr"
repo=$(new_repo $H); active_plan "$repo"
run_hook "$repo" $H "$(json_file "$repo/app/x.py")" BRANCH_ISOLATION_REASON="hotfix"
assert_rc_contains 0 "[BRANCH-ISOLATION]"

t "break-glass works for the tiny lane too (no plan present)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file "$repo/app/x.py")" BRANCH_ISOLATION_REASON="hotfix"
assert_rc_contains 0 "[BRANCH-ISOLATION]"

t "HARNESS_SHARED_BRANCHES override: main not listed → allow"
repo=$(new_repo $H); active_plan "$repo"
run_hook "$repo" $H "$(json_file "$repo/app/x.py")" HARNESS_SHARED_BRANCHES="develop release"
assert_silent_ok

t "Codex multi-file specs-only patch stays writable on main"
repo=$(new_repo $H)
payload=$(codex_patch $'*** Begin Patch\n*** Update File: specs/demo/PLAN.md\n*** Add File: specs/demo/SUMMARY.md\n*** End Patch')
run_hook "$repo" $H "$payload"
assert_silent_ok

t "mixed bookkeeping/code patch is denied even when specs path is first"
repo=$(new_repo $H)
payload=$(codex_patch $'*** Begin Patch\n*** Update File: specs/demo/PLAN.md\n*** Add File: app/x.py\n*** End Patch')
run_hook "$repo" $H "$payload"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "move/delete patch is denied when any path is implementation"
repo=$(new_repo $H)
payload=$(codex_patch $'*** Begin Patch\n*** Update File: specs/demo/old.md\n*** Move to: app/current.py\n*** Delete File: app/unused.py\n*** End Patch')
run_hook "$repo" $H "$payload"
assert_rc_contains 0 'app/current.py'

t "partial traversal patch fails closed on a shared branch"
repo=$(new_repo $H)
payload=$(codex_patch $'*** Begin Patch\n*** Update File: specs/demo/PLAN.md\n*** Add File: ../escape.py\n*** End Patch')
run_hook "$repo" $H "$payload"
assert_rc_contains 0 'could not safely classify'

t "tool_name-less edit payload cannot slip through as an empty shell command"
# Regression (Phase-4 review F1): a leading newline before the patch marker used to
# classify as shell/known with zero paths, and the guard allowed it on main.
repo=$(new_repo $H)
run_hook "$repo" $H '{"turn_id":"t","hook_event_name":"PreToolUse","tool_input":{"command":"\n*** Begin Patch\n*** Update File: src/app.py\n*** End Patch"}}'
assert_rc_contains 0 'could not safely classify'

t "shell-classified payload on the edit matcher is denied, not allowed empty"
repo=$(new_repo $H)
run_hook "$repo" $H '{"turn_id":"t","hook_event_name":"PreToolUse","tool_input":{"command":"echo hello"}}'
assert_rc_contains 0 'could not safely classify'

t "malformed payload fails closed on a shared branch"
repo=$(new_repo $H)
run_hook "$repo" $H '{not-json'
assert_rc_contains 0 'could not safely classify'

t "partial payload remains allowed on a task branch"
repo=$(new_repo $H); git -C "$repo" checkout -q -b feature/safe
payload=$(codex_patch $'*** Begin Patch\n*** Update File: app/x.py\n*** Add File: ../escape.py\n*** End Patch')
run_hook "$repo" $H "$payload"
assert_silent_ok

t "break-glass can override an unknown payload and records the audit"
repo=$(new_repo $H)
run_hook "$repo" $H '{not-json' BRANCH_ISOLATION_REASON="emergency payload recovery"
if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | grep -q 'break-glass override' && grep -q 'unparsed-edit-payload' "$repo/docs/harness-experimental/break-glass-log.md"; then pass
else fail "override/audit missing: rc=$RC out=$OUT"; fi

# linked_worktree <repo> <branch> — commit once, then add <repo>/.worktrees/<branch> on <branch>
linked_worktree() {
  git -C "$1" commit -q --allow-empty -m init
  git -C "$1" worktree add -q "$1/.worktrees/$2" -b "$2"
  echo "$1/.worktrees/$2"
}

t "session root on main, edit inside a linked worktree on a task branch → allow"
# Regression: ROOT came from CLAUDE_PROJECT_DIR (the main checkout), so the guard read
# `main` and denied every Edit/Write made inside a .worktrees/ checkout.
repo=$(new_repo $H); wt=$(linked_worktree "$repo" feature/wt)
run_hook "$repo" $H "$(json_file "$wt/app/x.py")" CLAUDE_PROJECT_DIR="$repo"
assert_silent_ok

t "new file in a not-yet-created dir inside the worktree → allow (walks up to an existing dir)"
repo=$(new_repo $H); wt=$(linked_worktree "$repo" feature/wt)
run_hook "$repo" $H "$(json_file "$wt/new/deep/dir/y.py")" CLAUDE_PROJECT_DIR="$repo"
assert_silent_ok

t "session root in a task worktree, edit in the main checkout on main → DENY"
# The reverse direction: launching from a feature worktree must not whitelist main.
repo=$(new_repo $H); wt=$(linked_worktree "$repo" feature/wt)
run_hook "$repo" $H "$(json_file "$repo/app/x.py")" CLAUDE_PROJECT_DIR="$wt"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "nested repo on a task branch inside a main checkout cannot re-home the check → DENY"
# A path must not pick its own judge: only the launch repo's linked worktrees re-home.
repo=$(new_repo $H); mkdir -p "$repo/hooks/inner"
git -C "$repo/hooks/inner" init -q -b tmpbr
run_hook "$repo" $H "$(json_file "$repo/hooks/inner/x.sh")" CLAUDE_PROJECT_DIR="$repo"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "session root in a task worktree, edit under the main checkout's .git/ → DENY"
repo=$(new_repo $H); wt=$(linked_worktree "$repo" feature/wt)
run_hook "$repo" $H "$(json_file "$repo/.git/hooks/pre-commit")" CLAUDE_PROJECT_DIR="$wt"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "break-glass log stays in the launch repo when the edit targets a worktree checkout"
repo=$(new_repo $H); wt=$(linked_worktree "$repo" feature/wt)
run_hook "$repo" $H "$(json_file "$repo/app/x.py")" CLAUDE_PROJECT_DIR="$wt" BRANCH_ISOLATION_REASON="why"
if [ -f "$wt/docs/harness-experimental/break-glass-log.md" ] && [ ! -e "$repo/docs/harness-experimental" ]; then pass
else fail "log not pinned to launch root: out=$OUT"; fi

t "session launched outside any repo, edit in a checkout on main → DENY"
repo=$(new_repo $H); outside=$(mktemp -d); _CLEANUP_DIRS+=("$outside")
run_hook "$repo" $H "$(json_file "$repo/app/x.py")" CLAUDE_PROJECT_DIR="$outside"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "separate git dir: editing its hooks from a checkout on main → DENY"
base=$(mktemp -d); _CLEANUP_DIRS+=("$base")
git -C "$base" init -q -b main --separate-git-dir="$base/gd" wt
mkdir -p "$base/wt/hooks" && cp -R "$ROOT/hooks/lib" "$base/wt/hooks/" && cp "$ROOT/hooks/$H" "$base/wt/hooks/"
run_hook "$base/wt" $H "$(json_file "$base/gd/hooks/pre-commit")" CLAUDE_PROJECT_DIR="$base/wt"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "bare git dir on main: editing its hooks from its task worktree → DENY"
repo=$(new_repo $H); git -C "$repo" commit -q --allow-empty -m init
base=$(mktemp -d); _CLEANUP_DIRS+=("$base")
git clone -q --bare "$repo" "$base/bare.git"
git -C "$base/bare.git" worktree add -q "$base/bwt" -b feature/b
mkdir -p "$base/bwt/hooks" && cp -R "$ROOT/hooks/lib" "$base/bwt/hooks/" && cp "$ROOT/hooks/$H" "$base/bwt/hooks/"
run_hook "$base/bwt" $H "$(json_file "$base/bare.git/hooks/post-receive")" CLAUDE_PROJECT_DIR="$base/bwt"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "file_path with an embedded newline is not resolved through the worktree → DENY"
repo=$(new_repo $H); wt=$(linked_worktree "$repo" feature/wt)
payload=$(jq -cn --arg f "$wt/x
$repo/app/a.py" '{tool_input:{file_path:$f}}')
run_hook "$repo" $H "$payload" CLAUDE_PROJECT_DIR="$repo"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "gitfile/core.worktree loop terminates instead of hanging the hook"
base=$(mktemp -d); _CLEANUP_DIRS+=("$base")
mkdir -p "$base/outer/inner/hooks"; git -C "$base/outer/inner" init -q -b feature/x
git -C "$base/outer/inner" commit -q --allow-empty -m i
printf 'gitdir: %s\n' "$base/outer/inner/.git" > "$base/outer/.git"
git -C "$base/outer/inner" config core.worktree "$base/outer/inner"
cp -R "$ROOT/hooks/lib" "$base/outer/inner/hooks/" && cp "$ROOT/hooks/$H" "$base/outer/inner/hooks/"
OUT=$(cd "$base/outer/inner" && printf '%s' "$(json_file "$base/outer/inner/app/x.py")" \
  | env CLAUDE_PROJECT_DIR="$base" perl -e 'alarm 10; exec @ARGV' bash "hooks/$H" 2>&1); RC=$?
assert_silent_ok

t "nested repo on a task branch inside a task worktree nested in main → allow"
repo=$(new_repo $H); wt=$(linked_worktree "$repo" feature/wt)
mkdir -p "$wt/vendor/nested"; git -C "$wt/vendor/nested" init -q -b feature/n
run_hook "$repo" $H "$(json_file "$wt/vendor/nested/app/x.py")" CLAUDE_PROJECT_DIR="$repo"
assert_silent_ok

# Fast path: a Claude Write/Edit payload is decided in bash+jq alone. NOPY is a PATH holding
# only the binaries the hook needs — python3 is deliberately absent, so the normalizer is
# unavailable and any fall-through to it fails closed.
NOPY=$(mktemp -d); _CLEANUP_DIRS+=("$NOPY")
for b in bash git jq dirname basename cat paste date mkdir; do ln -s "$(command -v "$b")" "$NOPY/$b"; done
claude_edit() { jq -cn --arg t "$1" --arg f "$2" '{hook_event_name:"PreToolUse",tool_name:$t,tool_input:{file_path:$f}}'; }

t "no python3: Claude Write to a code path on main → DENY"
repo=$(new_repo $H)
run_hook "$repo" $H "$(claude_edit Write "$repo/app/x.py")" PATH="$NOPY"
assert_rc_contains 0 'You are on shared branch main'

t "no python3: Claude Edit to a relative code path on main → DENY"
repo=$(new_repo $H)
run_hook "$repo" $H "$(claude_edit Edit app/x.py)" PATH="$NOPY"
assert_rc_contains 0 'You are on shared branch main'

t "no python3: Claude Write to specs/x/SUMMARY.md on main → allow"
repo=$(new_repo $H)
run_hook "$repo" $H "$(claude_edit Write "$repo/specs/x/SUMMARY.md")" PATH="$NOPY"
assert_silent_ok

t "no python3: specs path reached through a symlinked root still resolves → allow"
# macOS /var → /private/var: ROOT and the edit path must be compared after resolution.
repo=$(new_repo $H); link=$(mktemp -d); _CLEANUP_DIRS+=("$link"); ln -s "$repo" "$link/r"
run_hook "$repo" $H "$(claude_edit Write "$link/r/specs/x/SUMMARY.md")" PATH="$NOPY" CLAUDE_PROJECT_DIR="$link/r"
assert_silent_ok

t "no python3: Claude Write outside the repo on main → fails closed (not fast-pathed)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(claude_edit Write "specs/../../escape.py")" PATH="$NOPY"
assert_rc_contains 0 'could not safely classify'

t "no python3: Claude Write to the repository root on main → fails closed"
repo=$(new_repo $H)
run_hook "$repo" $H "$(claude_edit Write "$repo")" PATH="$NOPY"
assert_rc_contains 0 'could not safely classify'

t "no python3: Write payload carrying a prompt key is not fast-pathed → fails closed"
repo=$(new_repo $H)
run_hook "$repo" $H "$(jq -cn --arg f "$repo/specs/x/SUMMARY.md" '{hook_event_name:"PreToolUse",tool_name:"Write",prompt:"x",tool_input:{file_path:$f}}')" PATH="$NOPY"
assert_rc_contains 0 'could not safely classify'

t "no python3: codex apply_patch on main still fails closed"
repo=$(new_repo $H)
run_hook "$repo" $H "$(codex_patch $'*** Begin Patch\n*** Update File: specs/demo/PLAN.md\n*** End Patch')" PATH="$NOPY"
assert_rc_contains 0 'could not safely classify'

finish
