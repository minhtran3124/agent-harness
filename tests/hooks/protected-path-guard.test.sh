#!/bin/bash
# Contract tests for hooks/protected-path-guard.sh — deny Edit/Write to high-blast files
# unless PROTECTED_PATH_REASON is set (break-glass). Emits permissionDecision:deny JSON.
source "$(dirname "$0")/../lib.sh"

H=protected-path-guard.sh

t "write to settings.json → deny JSON"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file 'settings.json')"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "write to a hook script → deny JSON"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file 'hooks/commit-quality-gate.sh')"
assert_rc_contains 0 'High-blast-radius file'

t "write to run-tests.sh → deny JSON"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file 'scripts/run-tests.sh')"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "write to SUMMARY template → deny JSON"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file 'templates/SUMMARY.template.md')"
assert_rc_contains 0 '"permissionDecision":"deny"'

t "ordinary app file → silent allow"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file 'app/services/foo.py')"
assert_silent_ok

t "a non-hook file under tests/hooks/ is not protected → allow"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file 'tests/hooks/foo.test.sh')"
assert_silent_ok

t "break-glass: PROTECTED_PATH_REASON set → allow (exit 0, no deny)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_file 'settings.json')" PROTECTED_PATH_REASON='wiring new hook, approved'
assert_rc_contains 0 'break-glass override'

t "empty file_path → silent allow"
repo=$(new_repo $H)
run_hook "$repo" $H '{"tool_input":{}}'
assert_silent_ok

finish
