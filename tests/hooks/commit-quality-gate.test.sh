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
VERIFY_HEADER=$'Lane: normal\nConfidence: high\nReason: exercise the Verify re-run gate\n\n'
VERIFY_TABLE_OK="${VERIFY_HEADER}"$'### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| ok | test 1 = 1 | 0 | matches |\n'
VERIFY_TABLE_BAD="${VERIFY_HEADER}"$'### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| bad | false | 0 | claimed 0 but exits 1 |\n'

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

# ── Check 1.6: lane evidence (mechanizes rules/auto-correct-scope.md) ──
# Wired in response to the PR #119 review: lane evidence was proven by
# unit tests but never invoked against a real SUMMARY.
LANE_PY="$ROOT/scripts/verify_summary.py"
LANE_TINY=$'Lane: tiny\nConfidence: high\nReason: a real filled reason\n'
LANE_NORMAL_BAD=$'Lane: normal\nConfidence: high\nReason: a real filled reason\n\n### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| p | `<command>` | 0 | placeholder only |\n'
LANE_NORMAL_OK=$'Lane: normal\nConfidence: high\nReason: a real filled reason\n\n### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| p | `true` | 0 | a real command |\n'

t "Check 1.6: normal lane whose ### Verify holds only placeholders → BLOCKED"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$LANE_PY" "$repo/scripts/"
stage "$repo" "specs/demo/SUMMARY.md" "$LANE_NORMAL_BAD"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "Lane evidence... FAILED"

t "Check 1.6: the block names the real SUMMARY path, not the temp file"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$LANE_PY" "$repo/scripts/"
stage "$repo" "specs/demo/SUMMARY.md" "$LANE_NORMAL_BAD"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "specs/demo/SUMMARY.md"

t "Check 1.6: normal lane with a real ### Verify row → PASSES"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$LANE_PY" "$repo/scripts/"
stage "$repo" "specs/demo/SUMMARY.md" "$LANE_NORMAL_OK"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Lane evidence... PASSED"

t "Check 1.6: tiny lane needs only a filled header (evidence scales with lane)"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$LANE_PY" "$repo/scripts/"
stage "$repo" "specs/demo/SUMMARY.md" "$LANE_TINY"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Lane evidence... PASSED"

t "Check 1.6: same commit fixing the evidence self-unblocks (staged copy wins)"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$LANE_PY" "$repo/scripts/"
mkdir -p "$repo/specs/demo"
printf '%s\n' "$LANE_NORMAL_BAD" > "$repo/specs/demo/SUMMARY.md"   # failing copy on disk
git -C "$repo" add -f specs/demo/SUMMARY.md
printf '%s\n' "$LANE_NORMAL_OK" > "$repo/specs/demo/SUMMARY.md"    # fixed, then staged
git -C "$repo" add -f specs/demo/SUMMARY.md
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "Lane evidence... PASSED"

t "Check 1.6: a commit touching no specs/ path is unaffected"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$LANE_PY" "$repo/scripts/"
mkdir -p "$repo/specs/other"
printf '%s\n' "$LANE_NORMAL_BAD" > "$repo/specs/other/SUMMARY.md"
stage "$repo" "README.md" "docs only"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "Check 1.6: a slug dir with no SUMMARY.md (PLAN only) does not block"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$LANE_PY" "$repo/scripts/"
stage "$repo" "specs/demo/PLAN.md" "# plan"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "Check 1.6: python3 absent → skip with a notice, never block (fail-open)"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$LANE_PY" "$repo/scripts/"
stage "$repo" "specs/demo/SUMMARY.md" "$LANE_NORMAL_BAD"
nopy2=$(mktemp -d); _CLEANUP_DIRS+=("$nopy2")
IFS=: read -ra _pd2 <<< "$PATH"
for d in "${_pd2[@]}"; do
  [ -d "$d" ] || continue
  for f in "$d"/*; do
    b=$(basename "$f")
    case "$b" in python|python3|python3.*) continue ;; esac
    [ -e "$nopy2/$b" ] || ln -s "$f" "$nopy2/$b" 2>/dev/null
  done
done
run_hook "$repo" $H "$COMMIT_JSON" PATH="$nopy2"
assert_rc_contains 0 "Lane evidence skipped"

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
