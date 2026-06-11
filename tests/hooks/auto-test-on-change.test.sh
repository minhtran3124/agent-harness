#!/bin/bash
# Contract tests for hooks/auto-test-on-change.sh — the multi-ecosystem auto-test hook.
# Frozen from the 11-case matrix that shipped the rewrite (commit 3bfb96e).
source "$(dirname "$0")/../lib.sh"

H=auto-test-on-change.sh

# ---- Python (real pytest via shared venv) ----
if ensure_pyenv; then
  proj=$(new_repo $H)
  touch "$proj/pytest.ini"
  mkdir -p "$proj/tests"
  printf 'def test_ok():\n    assert True\n' > "$proj/tests/test_ok.py"
  printf 'def test_no():\n    assert False\n' > "$proj/tests/test_no.py"

  t "python: passing test reports PASSED"
  run_hook "$proj" $H "$(json_file "$proj/tests/test_ok.py")" PATH="$PYSHIM:$PATH"
  assert_rc_contains 0 "PASSED"

  t "python: failing test reports FAILED (never blocks)"
  run_hook "$proj" $H "$(json_file "$proj/tests/test_no.py")" PATH="$PYSHIM:$PATH"
  assert_rc_contains 0 "FAILED"
else
  t "python cases"; skip "python3 venv with pytest unavailable"
fi

# ---- Go (real go test) ----
if command -v go >/dev/null 2>&1; then
  gop=$(new_repo $H)
  (cd "$gop" && go mod init tmp/harness >/dev/null 2>&1)
  printf 'package h\nimport "testing"\nfunc TestOK(t *testing.T) {}\n' > "$gop/ok_test.go"

  t "go: passing package reports PASSED"
  run_hook "$gop" $H "$(json_file "$gop/ok_test.go")"
  assert_rc_contains 0 "PASSED"

  t "go: failing package reports FAILED"
  printf 'package h\nimport "testing"\nfunc TestNo(t *testing.T) { t.Fatal("x") }\n' > "$gop/no_test.go"
  run_hook "$gop" $H "$(json_file "$gop/no_test.go")"
  assert_rc_contains 0 "FAILED"
else
  t "go cases"; skip "go not installed"
fi

# ---- JS/TS runner resolution (npx shimmed — no node needed) ----
NPXSHIM=$(mktemp -d); _CLEANUP_DIRS+=("$NPXSHIM")
printf '#!/bin/bash\necho "SHIM-NPX: $*"\nexit 0\n' > "$NPXSHIM/npx" && chmod +x "$NPXSHIM/npx"

t "js: vitest in devDependencies → npx vitest run <file>"
jsp=$(new_repo $H)
echo '{"devDependencies":{"vitest":"^2.0.0"}}' > "$jsp/package.json"
mkdir -p "$jsp/src" && echo 'export {}' > "$jsp/src/foo.test.ts"
run_hook "$jsp" $H "$(json_file "$jsp/src/foo.test.ts")" PATH="$NPXSHIM:$PATH"
assert_rc_contains 0 "SHIM-NPX: vitest run"

t "js: jest resolved for a file under __tests__/"
jsp=$(new_repo $H)
echo '{"devDependencies":{"jest":"^29.0.0"}}' > "$jsp/package.json"
mkdir -p "$jsp/__tests__" && echo 'test("x",()=>{})' > "$jsp/__tests__/bar.jsx"
run_hook "$jsp" $H "$(json_file "$jsp/__tests__/bar.jsx")" PATH="$NPXSHIM:$PATH"
assert_rc_contains 0 "SHIM-NPX: jest"

if command -v npm >/dev/null 2>&1; then
  t "js: scripts.test fallback runs via npm"
  jsp=$(new_repo $H)
  printf '{"scripts":{"test":"node -e \\"process.exit(0)\\""}}' > "$jsp/package.json"
  echo 'x' > "$jsp/app.spec.js"
  run_hook "$jsp" $H "$(json_file "$jsp/app.spec.js")"
  assert_rc_contains 0 "PASSED"
else
  t "js npm fallback"; skip "npm not installed"
fi

t "js: no detectable runner → silent skip"
jsp=$(new_repo $H)
echo '{}' > "$jsp/package.json"
echo 'x' > "$jsp/app.spec.js"
run_hook "$jsp" $H "$(json_file "$jsp/app.spec.js")" PATH="$NPXSHIM:$PATH"
assert_silent_ok

# ---- Custom ecosystem override ----
t "custom: AUTO_TEST_CMD + AUTO_TEST_PATTERN covers an unlisted ecosystem"
cp=$(new_repo $H)
echo 'puts 1' > "$cp/foo_spec.rb"
run_hook "$cp" $H "$(json_file "$cp/foo_spec.rb")" AUTO_TEST_CMD='echo CUSTOM-RUN {file}' AUTO_TEST_PATTERN='*_spec.rb'
assert_rc_contains 0 "CUSTOM-RUN $cp/foo_spec.rb"

t "custom: AUTO_TEST_CMD alone replaces the detected runner"
cp=$(new_repo $H)
mkdir -p "$cp/tests" && touch "$cp/pytest.ini"
echo 'def test_x(): pass' > "$cp/tests/test_x.py"
run_hook "$cp" $H "$(json_file "$cp/tests/test_x.py")" AUTO_TEST_CMD='echo OVERRIDE {file}'
assert_rc_contains 0 "OVERRIDE"

# ---- Skips ----
t "non-test file → silent skip"
sp=$(new_repo $H)
echo 'x' > "$sp/notes.txt"
run_hook "$sp" $H "$(json_file "$sp/notes.txt")"
assert_silent_ok

t "plain .ts outside __tests__/ → silent skip"
sp=$(new_repo $H)
echo '{}' > "$sp/package.json"
mkdir -p "$sp/src" && echo 'x' > "$sp/src/util.ts"
run_hook "$sp" $H "$(json_file "$sp/src/util.ts")" PATH="$NPXSHIM:$PATH"
assert_silent_ok

t "missing file path in payload → silent skip"
sp=$(new_repo $H)
run_hook "$sp" $H '{"tool_input":{}}'
assert_silent_ok

finish
