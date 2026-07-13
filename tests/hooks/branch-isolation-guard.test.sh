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

finish
