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

# ── Dedup via hooks/lib/lane.sh: don't repeat the nudge once intake already ran ──

t "implementation intent, no plan, but a status:active PLAN.md exists → silent (already routed)"
repo=$(new_repo $H)
mkdir -p "$repo/specs/demo"
cat > "$repo/specs/demo/PLAN.md" <<'EOF'
---
status: active
---
EOF
run_hook "$repo" $H "$(json_prompt 'please add a new endpoint to handle user signup today')"
assert_silent_ok

t "implementation intent, no plan, but specs/ has an uncommitted change (tiny-lane SUMMARY just written) → silent"
repo=$(new_repo $H)
stage "$repo" "specs/demo/SUMMARY.md" "Lane: tiny"
run_hook "$repo" $H "$(json_prompt 'please add a new endpoint to handle user signup today')"
assert_silent_ok

t "implementation intent, no plan, specs/ present but all committed (no active plan) → still nudges"
repo=$(new_repo $H)
mkdir -p "$repo/specs/shipped-demo"
printf 'Lane: tiny\n' > "$repo/specs/shipped-demo/SUMMARY.md"
git -C "$repo" add -f specs/shipped-demo/SUMMARY.md >/dev/null 2>&1
git -C "$repo" commit -qm "seed shipped spec" >/dev/null 2>&1
run_hook "$repo" $H "$(json_prompt 'please add a new endpoint to handle user signup today')"
assert_rc_contains 0 "Run /feature-intake"

t "Codex UserPromptSubmit receives the same planning nudge"
repo=$(new_repo $H)
payload=$(jq -cn --arg prompt 'please add a new endpoint to handle user signup today' '{turn_id:"turn-redacted",hook_event_name:"UserPromptSubmit",prompt:$prompt}')
run_hook "$repo" $H "$payload"
assert_rc_contains 0 'Run /feature-intake'

t "malformed prompt payload is fail-visible but remains non-blocking"
repo=$(new_repo $H)
run_hook "$repo" $H '{not-json'
assert_rc_contains 0 'could not be classified'

t "missing prompt is fail-visible but remains non-blocking"
repo=$(new_repo $H)
run_hook "$repo" $H '{"turn_id":"t","hook_event_name":"UserPromptSubmit"}'
assert_rc_contains 0 'prompt-missing'

finish
