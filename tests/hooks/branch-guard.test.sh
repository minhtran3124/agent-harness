#!/bin/bash
# Contract tests for hooks/branch-guard.sh — warn (never block) on commit to main/master.
source "$(dirname "$0")/../lib.sh"

H=branch-guard.sh
COMMIT_JSON=$(json_cmd 'git commit -m x')

t "non-commit command is ignored (silent, exit 0)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_cmd 'git status')"
assert_silent_ok

t "commit on main warns but never blocks (exit 0)"
repo=$(new_repo $H)   # new_repo inits on 'main'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "[BRANCH GUARD]"

t "commit on a feature branch is silent"
repo=$(new_repo $H)
git -C "$repo" checkout -q -b feature/x
run_hook "$repo" $H "$COMMIT_JSON"
assert_silent_ok

finish
