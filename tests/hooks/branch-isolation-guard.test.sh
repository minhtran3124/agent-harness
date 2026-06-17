#!/bin/bash
# Contract tests for hooks/branch-isolation-guard.sh — hard-block code edits on a shared
# branch while a plan is `status: active`, with a break-glass override.
source "$(dirname "$0")/../lib.sh"

H=branch-isolation-guard.sh

# active_plan <repo> — drop a specs/<slug>/PLAN.md with status: active into the repo
active_plan() {
  mkdir -p "$1/specs/demo"
  printf -- '---\nslug: demo\nstatus: active\n---\n# Demo\n' > "$1/specs/demo/PLAN.md"
}

t "no active plan → allow even on main (silent, exit 0)"
repo=$(new_repo $H)   # new_repo inits on 'main'
run_hook "$repo" $H "$(json_file "$repo/app/x.py")"
assert_silent_ok

t "on main + active plan + code file → DENY"
repo=$(new_repo $H); active_plan "$repo"
run_hook "$repo" $H "$(json_file "$repo/app/x.py")"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "on main + active plan + specs/ bookkeeping file → allow (exempt)"
repo=$(new_repo $H); active_plan "$repo"
run_hook "$repo" $H "$(json_file "$repo/specs/demo/PLAN.md")"
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

t "HARNESS_SHARED_BRANCHES override: main not listed → allow"
repo=$(new_repo $H); active_plan "$repo"
run_hook "$repo" $H "$(json_file "$repo/app/x.py")" HARNESS_SHARED_BRANCHES="develop release"
assert_silent_ok

finish
