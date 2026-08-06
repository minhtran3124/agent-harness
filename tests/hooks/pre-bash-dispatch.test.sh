#!/bin/bash
# Contract tests for hooks/pre-bash-dispatch.sh — single Bash PreToolUse entrypoint.
source "$(dirname "$0")/../lib.sh"

H=pre-bash-dispatch.sh

# Dispatcher needs the four child hooks + shared libs in the throwaway repo.
dispatch_repo() {
  new_repo "$H" check-untracked-py.sh commit-quality-gate.sh risk-corroboration.sh branch-guard.sh
}

t "non-commit command is ignored (silent)"
repo=$(dispatch_repo)
printf 'x\n' > "$repo/loose.py"
run_hook "$repo" $H "$(json_cmd 'ls')"
assert_silent_ok

t "untracked .py + git commit → deny JSON (forwards untracked-py)"
repo=$(dispatch_repo)
printf 'x\n' > "$repo/loose.py"
run_hook "$repo" $H "$(json_cmd 'git commit -m x')"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "untracked .py + git push → deny JSON"
repo=$(dispatch_repo)
printf 'x\n' > "$repo/loose.py"
run_hook "$repo" $H "$(json_cmd 'git push origin main')"
assert_rc_contains 0 'Untracked .py'

t "no untracked .py on commit → allows past untracked (may run quality/risk)"
repo=$(dispatch_repo)
stage "$repo" "ok.txt" "x"
run_hook "$repo" $H "$(json_cmd 'git commit -m x')"
assert_rc 0

t "missing git-command lib fails closed on commit"
repo=$(dispatch_repo)
rm -rf "$repo/hooks/lib"
run_hook "$repo" $H "$(json_cmd 'git commit -m x')"
assert_rc 2

t "branch-guard warn still surfaces on commit on main"
repo=$(dispatch_repo)
stage "$repo" "ok.txt" "x"
# Ensure no untracked py; commit quality/risk should pass empty/minimal staged
run_hook "$repo" $H "$(json_cmd 'git commit -m x')"
assert_rc_contains 0 "BRANCH GUARD"

finish
