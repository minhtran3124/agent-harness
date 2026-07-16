#!/bin/bash
# Contract tests for hooks/commit-quality-gate.sh — secrets / debug artifacts / evidence /
# targeted tests. The "failing test BLOCKS" case is the regression guard for the `|| true`
# status-swallow bug (same defect class as auto-test-on-change, commit 78b28a0).
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

# ── Task 3.2: REQUIRE_VERIFY=1 re-runs the ### Verify table (machine-verified proof) ──
VERIFY_PY="$ROOT/scripts/verify_summary.py"
VERIFY_TABLE_OK=$'### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| ok | test 1 = 1 | 0 | matches |\n'
VERIFY_TABLE_BAD=$'### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| bad | false | 0 | claimed 0 but exits 1 |\n'

t "REQUIRE_VERIFY=1: ### Verify table whose command matches its claimed exit → re-run PASSES"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$VERIFY_PY" "$repo/scripts/"
stage "$repo" "app/services/calc.py" 'x = 1'
stage "$repo" "specs/x/SUMMARY.md" "$VERIFY_TABLE_OK"
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_VERIFY=1
assert_rc_contains 0 "Evidence (### Verify re-run)... PASSED"

t "REQUIRE_VERIFY=1: claimed Exit != actual exit → re-run BLOCKS (exit 2)"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$VERIFY_PY" "$repo/scripts/"
stage "$repo" "app/services/calc.py" 'x = 1'
stage "$repo" "specs/x/SUMMARY.md" "$VERIFY_TABLE_BAD"
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_VERIFY=1
assert_rc_contains 2 "Evidence (### Verify re-run)... FAILED"

t "REQUIRE_VERIFY=1: python3 absent → degrade (warn, do not block) even with a mismatch"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$VERIFY_PY" "$repo/scripts/"
stage "$repo" "app/services/calc.py" 'x = 1'
stage "$repo" "specs/x/SUMMARY.md" "$VERIFY_TABLE_BAD"
# Build a PATH mirror with every binary EXCEPT python/python3 so `command -v python3` fails
nopy=$(mktemp -d); _CLEANUP_DIRS+=("$nopy")
IFS=: read -ra _pd <<< "$PATH"
for d in "${_pd[@]}"; do
  [ -d "$d" ] || continue
  for f in "$d"/*; do
    b=$(basename "$f")
    case "$b" in python|python3|python3.*) continue ;; esac
    [ -e "$nopy/$b" ] || ln -s "$f" "$nopy/$b" 2>/dev/null
  done
done
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_VERIFY=1 PATH="$nopy"
assert_rc_contains 0 "Evidence re-run skipped"

t "REQUIRE_VERIFY=0 (default): a mismatching ### Verify table is NOT re-run (regression)"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$VERIFY_PY" "$repo/scripts/"
stage "$repo" "app/services/calc.py" 'x = 1'
stage "$repo" "specs/x/SUMMARY.md" "$VERIFY_TABLE_BAD"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

# Check 1.5: pending escalations (deny-on-no-response, review C5)
t "staged spec file + pending escalation in that slug → BLOCKED (exit 2)"
repo=$(new_repo $H)
stage "$repo" "specs/demo/SUMMARY.md" "Lane: normal"
stage "$repo" "specs/demo/ESCALATIONS.md" '## E001
- question: widen the regex?
- decision: pending'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "deny-on-no-response"

t "same commit recording the decision self-unblocks (staged copy wins)"
repo=$(new_repo $H)
stage "$repo" "specs/demo/SUMMARY.md" "Lane: normal"
stage "$repo" "specs/demo/ESCALATIONS.md" '## E001
- question: widen the regex?
- decision: A (accepted)
- decided_by: human
- decided_at: 2026-07-16'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Escalations... PASSED"

t "pending escalation on disk does NOT block commits that leave the slug untouched"
repo=$(new_repo $H)
mkdir -p "$repo/specs/other"
printf -- '- decision: pending\n' > "$repo/specs/other/ESCALATIONS.md"
stage "$repo" "README.md" "docs change"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "unstaged pending ESCALATIONS.md on disk still blocks a commit touching its slug"
repo=$(new_repo $H)
mkdir -p "$repo/specs/demo"
printf -- '- decision: pending\n' > "$repo/specs/demo/ESCALATIONS.md"
stage "$repo" "specs/demo/SUMMARY.md" "Lane: normal"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "deny-on-no-response"

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

  t "failing matching test BLOCKS the commit (exit 2)"
  repo=$(new_repo $H)
  stage "$repo" "app/services/calc.py" 'def add(a, b): return a + b'
  stage "$repo" "tests/services/test_calc.py" 'def test_add(): assert False'
  run_hook "$repo" $H "$COMMIT_JSON" PATH="$PYSHIM:$PATH"
  assert_rc_contains 2 "Tests... FAILED"
else
  t "pytest-dependent cases"; skip "python3 venv with pytest unavailable"
fi

finish
