#!/bin/bash
# Contract tests for hooks/scope-gate.sh — UserPromptSubmit nudge when an implementation
# prompt references no plan. Pure function of .prompt; injects additionalContext, never denies.
source "$(dirname "$0")/../lib.sh"

H=scope-gate.sh

t "implementation intent, >6 words, no plan → injects guidance"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_prompt 'please add a new endpoint to handle user signup today')"
assert_rc_contains 0 "Run /feature-intake"

t "prompt referencing a plan path → silent"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_prompt 'implement the change described in specs/foo/PLAN.md now')"
assert_silent_ok

t "prompt mentioning the word plan → silent"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_prompt 'build the feature following the plan we agreed earlier')"
assert_silent_ok

t "short implementation prompt (<=6 words) → silent"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_prompt 'fix the bug')"
assert_silent_ok

t "non-implementation prompt → silent"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_prompt 'what does this repository do and how is it organized')"
assert_silent_ok

finish
