#!/bin/bash
# Integration: wrapped/prefixed git-commit commands reach a gate through real
# stdin JSON — proving the shared matcher is wired end-to-end, not just unit-
# tested. branch-guard is used because it is warn-only (zero side effects), so
# it safely exercises the full stdin→matcher→act path on a throwaway repo.
source "$(dirname "$0")/../lib.sh"

# new_repo inits on branch `main`, so branch-guard should warn on a recognized commit.
repo=$(new_repo branch-guard.sh)

for cmd in \
  'git commit -m x' \
  'cd /tmp && git commit' \
  'git -C . commit' \
  'command git commit' \
  'echo done; git commit'; do
  t "branch-guard warns on wrapped commit: $cmd"
  run_hook "$repo" branch-guard.sh "$(json_cmd "$cmd")"
  assert_rc_contains 0 "BRANCH GUARD"
done

t "branch-guard stays silent on a non-commit command"
run_hook "$repo" branch-guard.sh "$(json_cmd 'echo hi')"
assert_silent_ok

# F2 — missing matcher lib: blocking hooks fail CLOSED (exit 2); warn-only stays non-blocking.
norepo=$(new_repo check-untracked-py.sh branch-guard.sh)
rm -rf "$norepo/hooks/lib"

t "check-untracked-py fails closed (exit 2) when the matcher lib is missing"
run_hook "$norepo" check-untracked-py.sh "$(json_cmd 'git commit')"
assert_rc 2

t "branch-guard stays non-blocking (exit 0) when the matcher lib is missing"
run_hook "$norepo" branch-guard.sh "$(json_cmd 'git commit')"
assert_rc 0

finish
