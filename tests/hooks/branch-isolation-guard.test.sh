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

finish
