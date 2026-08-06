#!/bin/bash
# Contract tests for hooks/pre-bash-dispatch.sh — the single PreToolUse Bash hook that
# fans out to the four git-command sub-hooks in settings order.
#
# Invariant #1 (SC-1): each sub-hook's stdout is relayed UNCONDITIONALLY, regardless of
# its exit code. check-untracked-py.sh denies by printing a permissionDecision:"deny"
# JSON to stdout and then EXITING 0 — the dispatcher must still relay that deny, or a
# hard block becomes a silent no-op.
source "$(dirname "$0")/../lib.sh"

H=pre-bash-dispatch.sh
# The dispatcher spawns these four sub-hooks; all must travel into the throwaway repo.
SUBS="check-untracked-py.sh commit-quality-gate.sh risk-corroboration.sh branch-guard.sh"

t "non-commit/push command fast-paths silent exit 0 (no sub-hook runs)"
repo=$(new_repo $H $SUBS)
printf 'x\n' > "$repo/loose.py"   # untracked .py, but 'ls' is not commit/push
run_hook "$repo" $H "$(json_cmd 'ls')"
assert_silent_ok

t "commit with untracked .py → deny JSON relayed even though the sub-hook exits 0"
repo=$(new_repo $H $SUBS)
printf 'x\n' > "$repo/loose.py"
run_hook "$repo" $H "$(json_cmd 'git commit -m x')"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "commit with a staged secret → dispatcher propagates the exit-2 block"
repo=$(new_repo $H $SUBS)
stage "$repo" "config.py" 'password = "supersecretvalue123"'
run_hook "$repo" $H "$(json_cmd 'git commit -m x')"
assert_rc_contains 2 'Potential secrets'

t "git push with untracked .py → untracked-py acts (deny relayed at exit 0)"
repo=$(new_repo $H $SUBS)
printf 'x\n' > "$repo/loose.py"
run_hook "$repo" $H "$(json_cmd 'git push origin main')"
assert_rc_contains 0 'Untracked .py'

t "git push → commit-only gates stay silent (only untracked-py acts)"
assert_rc_not_contains 0 'COMMIT GATE'

finish
