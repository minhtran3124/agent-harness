#!/bin/bash
# Contract tests for hooks/commit-quality-gate.sh — secrets / debug artifacts / evidence /
# targeted tests. The pytest-block case is a KNOWN BUG (xfail): `|| true` swallows the
# pytest exit status (same defect class fixed in auto-test-on-change, commit 78b28a0),
# so a failing test suite cannot block a commit. The xfail flips to pass when fixed.
source "$(dirname "$0")/../lib.sh"

H=commit-quality-gate.sh
COMMIT_JSON=$(json_cmd 'git commit -m x')

t "non-commit command is ignored (silent, exit 0)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_cmd 'git push')"
assert_silent_ok

t "clean staged docs pass (no app/ files → skip tests)"
repo=$(new_repo $H)
stage "$repo" "README.md" "hello"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "No app/ Python files staged"

t "hardcoded api_key in staged code → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "config.py" 'api_key = "supersecret12345"'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "Potential secrets"

t "staged .env file → BLOCKED"
repo=$(new_repo $H)
stage "$repo" ".env" "X=1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 ".env file staged"

t "secret-looking string in tests/ is exempt"
repo=$(new_repo $H)
stage "$repo" "tests/fixtures.py" 'api_key = "fakefakefake12345"'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "breakpoint() added in app/ code → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "app/services/calc.py" 'breakpoint()'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "breakpoint"

t "bare print( added in app/ code → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "app/services/calc.py" 'print("debug")'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "bare print()"

t "REQUIRE_VERIFY=1: app/ staged without a ### Verify block → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "app/services/calc.py" 'x = 1'
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_VERIFY=1
assert_rc_contains 2 "### Verify"

t "REQUIRE_VERIFY=1: staged SUMMARY with ### Verify satisfies the gate"
repo=$(new_repo $H)
stage "$repo" "app/services/calc.py" 'x = 1'
stage "$repo" "specs/x/SUMMARY.md" '### Verify'
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_VERIFY=1
assert_rc_contains 0 "Evidence (### Verify present)... PASSED"

if ensure_pyenv; then
  t "matching passing test runs and commit is allowed"
  repo=$(new_repo $H)
  stage "$repo" "app/services/calc.py" 'def add(a, b): return a + b'
  stage "$repo" "tests/services/test_calc.py" 'def test_add(): assert 1 + 1 == 2'
  run_hook "$repo" $H "$COMMIT_JSON" PATH="$PYSHIM:$PATH"
  assert_rc_contains 0 "Tests... PASSED"

  t "≥5 app/ files staged → /compound crystallization hint"
  repo=$(new_repo $H)
  for i in 1 2 3 4 5; do stage "$repo" "app/services/m$i.py" "x = $i"; done
  stage "$repo" "tests/services/test_m1.py" 'def test_m(): assert True'
  run_hook "$repo" $H "$COMMIT_JSON" PATH="$PYSHIM:$PATH"
  assert_rc_contains 0 "Large session detected"

  t "failing matching test → should BLOCK (exit 2)"
  repo=$(new_repo $H)
  stage "$repo" "app/services/calc.py" 'def add(a, b): return a + b'
  stage "$repo" "tests/services/test_calc.py" 'def test_add(): assert False'
  run_hook "$repo" $H "$COMMIT_JSON" PATH="$PYSHIM:$PATH"
  if [ "$RC" -eq 2 ]; then
    pass  # bug fixed — gate blocks as documented
  else
    xfail "|| true at commit-quality-gate.sh:136 swallows pytest's exit status (rc=$RC)"
  fi
else
  t "pytest-dependent cases"; skip "python3 venv with pytest unavailable"
fi

finish
