#!/bin/bash
# Contract tests for hooks/check-untracked-py.sh — deny commit/push when untracked .py exist.
# The hook emits a permissionDecision:deny JSON on stdout (it does NOT exit 2).
source "$(dirname "$0")/../lib.sh"

H=check-untracked-py.sh

t "non-commit/push command is ignored (silent)"
repo=$(new_repo $H)
printf 'x\n' > "$repo/loose.py"   # untracked, but command is not commit/push
run_hook "$repo" $H "$(json_cmd 'git status')"
assert_silent_ok

t "untracked .py + git commit → deny JSON"
repo=$(new_repo $H)
printf 'x\n' > "$repo/loose.py"
run_hook "$repo" $H "$(json_cmd 'git commit -m x')"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "untracked .py + git push → deny JSON"
repo=$(new_repo $H)
printf 'x\n' > "$repo/loose.py"
run_hook "$repo" $H "$(json_cmd 'git push origin main')"
assert_rc_contains 0 'Untracked .py'

t "no untracked .py → silent allow"
repo=$(new_repo $H)
stage "$repo" "tracked.py" "x"
run_hook "$repo" $H "$(json_cmd 'git commit -m x')"
assert_silent_ok

t "untracked .py under a nested .claude/ is excluded by the hook's own guard"
repo=$(new_repo $H)
mkdir -p "$repo/app/.claude"
printf 'x\n' > "$repo/app/.claude/derived.py"   # not gitignored here → git lists it; hook's grep -v drops it
run_hook "$repo" $H "$(json_cmd 'git commit -m x')"
assert_silent_ok

finish
