#!/bin/bash
# Contract tests for hooks/commit-gate.sh — payload parse, the git commit/push filter,
# profile selection, and every check except the escalation / lane-evidence / run-state cases
# (tests/hooks/commit-gate-evidence.test.sh) and the risk-category cases
# (tests/hooks/commit-gate-risk.test.sh).
#
# The untracked-.py deny is stdout permissionDecision:"deny" JSON with exit 0; every other
# block is exit 2 with the message on stderr.
source "$(dirname "$0")/../lib.sh"

H=commit-gate.sh
# The real Claude Bash shape (tool_name present) takes the one-jq fast path, so it is what
# a PATH without python3 must still be able to gate. json_cmd (no tool_name) goes through the
# normalizer instead; both shapes are exercised below.
json_bash() { jq -cn --arg c "$1" '{tool_name:"Bash",tool_input:{command:$c}}'; }
COMMIT_JSON=$(json_bash 'git commit -m x')

# no_python_path → echoes a PATH mirror with every binary EXCEPT python/python3.
no_python_path() {
  local nopy d f b; nopy=$(mktemp -d); _CLEANUP_DIRS+=("$nopy")
  local -a pd; IFS=: read -ra pd <<< "$PATH"
  for d in "${pd[@]}"; do
    [ -d "$d" ] || continue
    for f in "$d"/*; do
      b=$(basename "$f")
      case "$b" in python|python3|python3.*) continue ;; esac
      [ -e "$nopy/$b" ] || ln -s "$f" "$nopy/$b" 2>/dev/null
    done
  done
  echo "$nopy"
}
NOPY=$(no_python_path)

t "commit-gate.sh is valid bash (bash -n)"
if bash -n "$ROOT/hooks/$H" 2>/dev/null; then pass; else fail "bash -n failed"; fi

# ── Parse + filter ────────────────────────────────────────────────────────
t "non-commit/push command fast-paths silent exit 0 (no check runs)"
repo=$(new_repo $H)
printf 'x\n' > "$repo/loose.py"   # untracked .py, but 'ls' is not commit/push
run_hook "$repo" $H "$(json_cmd 'ls')"
assert_silent_ok

t "non-git Claude Bash payload exits 0 silently with no python3 on PATH (one-jq fast path)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_bash 'ls -la')" PATH="$NOPY"
assert_silent_ok

t "strict: commit with untracked .py → deny JSON on stdout at exit 0"
repo=$(new_repo $H)
printf 'x\n' > "$repo/loose.py"
run_hook_args "$repo" $H "$(json_cmd 'git commit -m x')" --profile strict
assert_rc_contains 0 '"permissionDecision":"deny"'

t "commit with a staged secret → exit-2 block"
repo=$(new_repo $H)
stage "$repo" "config.py" 'password = "supersecretvalue123"'
run_hook "$repo" $H "$(json_cmd 'git commit -m x')"
assert_rc_contains 2 'Potential secrets'

t "strict: git push with untracked .py → check_untracked_py denies at exit 0"
repo=$(new_repo $H)
printf 'x\n' > "$repo/loose.py"
run_hook_args "$repo" $H "$(json_cmd 'git push origin main')" --profile strict
assert_rc_contains 0 'Untracked .py'

t "git push → commit-only checks stay silent (only check_untracked_py acts)"
assert_rc_not_contains 0 'COMMIT GATE'

t "strict: Codex Bash/unified-exec shape reaches the same git checks"
repo=$(new_repo $H)
printf 'x\n' > "$repo/loose.py"
payload=$(jq -cn '{turn_id:"turn-redacted",hook_event_name:"PreToolUse",tool_name:"Bash",tool_input:{command:"git push origin main"}}')
run_hook_args "$repo" $H "$payload" --profile strict
assert_rc_contains 0 'Untracked .py'

t "malformed Bash payload fails closed instead of fast-pathing"
repo=$(new_repo $H)
run_hook "$repo" $H '{not-json'
assert_rc_contains 2 'could not safely classify Bash payload'

t "missing command fails closed with an actionable diagnostic"
repo=$(new_repo $H)
run_hook "$repo" $H '{"turn_id":"t","hook_event_name":"PreToolUse","tool_name":"Bash","tool_input":{}}'
assert_rc_contains 2 'command-missing'

# Wrapped/prefixed commit commands reach the checks through real stdin JSON — the shared
# matcher is wired end-to-end, not just unit-tested.
repo=$(new_repo $H)
for cmd in \
  'git commit -m x' \
  'cd /tmp && git commit' \
  'git -C . commit' \
  'command git commit' \
  'echo done; git commit'; do
  t "wrapped commit reaches the checks: $cmd"
  run_hook "$repo" $H "$(json_cmd "$cmd")"
  assert_rc_contains 0 "Secrets scan... PASSED"
done

t "a non-commit command stays silent"
run_hook "$repo" $H "$(json_cmd 'echo hi')"
assert_silent_ok

t "fails closed (exit 2) when the git-command matcher lib is missing"
norepo=$(new_repo $H)
rm -f "$norepo/hooks/lib/git-command.sh"
run_hook "$norepo" $H "$(json_cmd 'git commit')"
assert_rc_contains 2 'matcher lib missing'

t "fails closed (exit 2) when the matcher lib defines only the commit-or-push matcher"
norepo=$(new_repo $H)
printf '%s\n' 'hook_cmd_is_git_commit_or_push() { return 0; }' > "$norepo/hooks/lib/git-command.sh"
run_hook "$norepo" $H "$(json_cmd 'git commit')"
assert_rc_contains 2 'matcher lib missing'

t "fails closed (exit 2) on commit when the lane lib is missing"
norepo=$(new_repo $H)
rm -f "$norepo/hooks/lib/lane.sh"
run_hook "$norepo" $H "$COMMIT_JSON"
assert_rc_contains 2 'lane lib missing'

# ── check_untracked_py (strict) ───────────────────────────────────────────
t "strict: non-commit/push command is ignored (silent)"
repo=$(new_repo $H)
printf 'x\n' > "$repo/loose.py"
run_hook_args "$repo" $H "$(json_cmd 'git status')" --profile strict
assert_silent_ok

t "strict: untracked .py + git commit → deny JSON"
repo=$(new_repo $H)
printf 'x\n' > "$repo/loose.py"
run_hook_args "$repo" $H "$(json_cmd 'git commit -m x')" --profile strict
assert_rc_contains 0 '"permissionDecision":"deny"'

t "strict: untracked .py + git push → deny JSON"
repo=$(new_repo $H)
printf 'x\n' > "$repo/loose.py"
run_hook_args "$repo" $H "$(json_cmd 'git push origin main')" --profile strict
assert_rc_contains 0 'Untracked .py'

t "strict: no untracked .py → no deny"
repo=$(new_repo $H)
stage "$repo" "tracked.py" "x"
run_hook_args "$repo" $H "$(json_cmd 'git commit -m x')" --profile strict
assert_rc_not_contains 0 'permissionDecision'

t "strict: untracked .py under a nested .claude/ is excluded"
repo=$(new_repo $H)
mkdir -p "$repo/app/.claude"
printf 'x\n' > "$repo/app/.claude/derived.py"   # not gitignored here → git lists it; the check drops it
run_hook_args "$repo" $H "$(json_cmd 'git commit -m x')" --profile strict
assert_rc_not_contains 0 'permissionDecision'

# Regression: the deployed harness lives at the repo ROOT, so `git ls-files` reports
# `.claude/skills/...` with NO leading slash. A `/\.claude/` pattern misses it and denies
# every commit in a fresh consumer whose .gitignore does not yet list .claude/.
t "strict: untracked .py under a ROOT-level .claude/ is also excluded (fresh-consumer install)"
repo=$(new_repo $H)
mkdir -p "$repo/.claude/skills/visual-planner"
printf 'x\n' > "$repo/.claude/skills/visual-planner/render_plan.py"
run_hook_args "$repo" $H "$(json_cmd 'git commit -m x')" --profile strict
assert_rc_not_contains 0 'permissionDecision'

t "strict: a real untracked .py still denies even when a root .claude/ is present"
repo=$(new_repo $H)
mkdir -p "$repo/.claude/skills/visual-planner"
printf 'x\n' > "$repo/.claude/skills/visual-planner/render_plan.py"
printf 'x\n' > "$repo/loose.py"
run_hook_args "$repo" $H "$(json_cmd 'git commit -m x')" --profile strict
assert_rc_contains 0 'loose.py'

# ── check_secrets ─────────────────────────────────────────────────────────
t "git push (standard) is ignored by the commit checks (silent, exit 0)"
repo=$(new_repo $H)
run_hook "$repo" $H "$(json_bash 'git push')"
assert_silent_ok

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

# The exemption is depth-independent: a bare ':!tests/' pathspec matches only a repo-root
# `tests/`, so a monorepo's own test tree was never exempt and blocked its placeholders.
t "secret-looking string in a NESTED tests/ dir is exempt"
repo=$(new_repo $H)
stage "$repo" "apps/api/tests/fixtures.py" 'api_key = "fakefakefake12345"'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

t "secret-looking string in a __tests__/ dir is exempt"
repo=$(new_repo $H)
stage "$repo" "apps/web/workers/__tests__/config.test.ts" "const SECRET = 'x'.repeat(32)"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc 0

# The exemption must not become a blanket pass: a path merely CONTAINING the word stays scanned.
t "secret-looking string in a non-test path containing 'tests' still BLOCKS"
repo=$(new_repo $H)
stage "$repo" "app/testsuite_config.py" 'api_key = "supersecret12345"'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 2 "Potential secrets"

t "python3 absent from PATH → the secrets check still blocks"
repo=$(new_repo $H)
stage "$repo" "config.py" 'api_key = "supersecret12345"'
run_hook "$repo" $H "$COMMIT_JSON" PATH="$NOPY"
assert_rc_contains 2 "Potential secrets"

# ── check_app_gates: opt-in via REQUIRE_APP_GATES=1 (or --profile strict) ──
t "clean staged docs pass with REQUIRE_APP_GATES=1 (no app/ files → skip tests)"
repo=$(new_repo $H)
stage "$repo" "README.md" "hello"
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1
assert_rc_contains 0 "No app/ Python files staged"

t "REQUIRE_APP_GATES unset (standard): breakpoint() in staged app/ does NOT block"
repo=$(new_repo $H)
stage "$repo" "app/services/calc.py" 'breakpoint()'
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "App checks"

t "REQUIRE_APP_GATES=1: breakpoint() added in app/ code → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "app/services/calc.py" 'breakpoint()'
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1
assert_rc_contains 2 "breakpoint"

t "REQUIRE_APP_GATES=1: bare print( added in app/ code → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "app/services/calc.py" 'print("debug")'
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1
assert_rc_contains 2 "bare print()"

t "REQUIRE_APP_GATES=1 + REQUIRE_VERIFY=1: app/ staged without a ### Verify block → BLOCKED"
repo=$(new_repo $H)
stage "$repo" "app/services/calc.py" 'x = 1'
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1 REQUIRE_VERIFY=1
assert_rc_contains 2 "### Verify"

t "REQUIRE_APP_GATES=1 + REQUIRE_VERIFY=1: staged SUMMARY with ### Verify satisfies the gate"
repo=$(new_repo $H)
stage "$repo" "app/services/calc.py" 'x = 1'
stage "$repo" "specs/x/SUMMARY.md" '### Verify'
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1 REQUIRE_VERIFY=1
assert_rc_contains 0 "Evidence (### Verify present)... PASSED"

# REQUIRE_VERIFY=1 re-runs the ### Verify table (machine-verified proof)
VERIFY_PY="$ROOT/scripts/verify_summary.py"
VERIFY_HEADER=$'Lane: normal\nConfidence: high\nReason: exercise the Verify re-run gate\n\n'
VERIFY_TABLE_OK="${VERIFY_HEADER}"$'### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| ok | test 1 = 1 | 0 | matches |\n'
VERIFY_TABLE_BAD="${VERIFY_HEADER}"$'### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| bad | false | 0 | claimed 0 but exits 1 |\n'

t "REQUIRE_VERIFY=1: ### Verify table whose command matches its claimed exit → re-run PASSES"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$VERIFY_PY" "$repo/scripts/"
stage "$repo" "app/services/calc.py" 'x = 1'
stage "$repo" "specs/x/SUMMARY.md" "$VERIFY_TABLE_OK"
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1 REQUIRE_VERIFY=1
assert_rc_contains 0 "Evidence (### Verify re-run)... PASSED"

t "REQUIRE_VERIFY=1: claimed Exit != actual exit → re-run BLOCKS (exit 2)"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$VERIFY_PY" "$repo/scripts/"
stage "$repo" "app/services/calc.py" 'x = 1'
stage "$repo" "specs/x/SUMMARY.md" "$VERIFY_TABLE_BAD"
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1 REQUIRE_VERIFY=1
assert_rc_contains 2 "Evidence (### Verify re-run)... FAILED"

t "REQUIRE_VERIFY=1: python3 absent → degrade (warn, do not block) even with a mismatch"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$VERIFY_PY" "$repo/scripts/"
stage "$repo" "app/services/calc.py" 'x = 1'
stage "$repo" "specs/x/SUMMARY.md" "$VERIFY_TABLE_BAD"
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1 REQUIRE_VERIFY=1 PATH="$NOPY"
assert_rc_contains 0 "Evidence re-run skipped"

t "REQUIRE_VERIFY=0 (default): a mismatching ### Verify table is NOT re-run (regression)"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$VERIFY_PY" "$repo/scripts/"
stage "$repo" "app/services/calc.py" 'x = 1'
stage "$repo" "specs/x/SUMMARY.md" "$VERIFY_TABLE_BAD"
run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1
assert_rc 0

if ensure_pyenv; then
  t "matching passing test runs and commit is allowed"
  repo=$(new_repo $H)
  stage "$repo" "app/services/calc.py" 'def add(a, b): return a + b'
  stage "$repo" "tests/services/test_calc.py" 'def test_add(): assert 1 + 1 == 2'
  run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1 PATH="$PYSHIM:$PATH"
  assert_rc_contains 0 "Tests... PASSED"

  t "≥5 app/ files staged → compound-skill crystallization hint"
  repo=$(new_repo $H)
  for i in 1 2 3 4 5; do stage "$repo" "app/services/m$i.py" "x = $i"; done
  stage "$repo" "tests/services/test_m1.py" 'def test_m(): assert True'
  run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1 PATH="$PYSHIM:$PATH"
  assert_rc_contains 0 "Large session detected"

  t "failing matching test BLOCKS the commit (exit 2)"
  repo=$(new_repo $H)
  stage "$repo" "app/services/calc.py" 'def add(a, b): return a + b'
  stage "$repo" "tests/services/test_calc.py" 'def test_add(): assert False'
  run_hook "$repo" $H "$COMMIT_JSON" REQUIRE_APP_GATES=1 PATH="$PYSHIM:$PATH"
  assert_rc_contains 2 "Tests... FAILED"
else
  t "pytest-dependent cases"; skip "python3 venv with pytest unavailable"
fi

# ── Repo-root resolution: never from the hook's own location ──────────────
# foreign_host → a git repo that HOSTS the hook but is NOT the project. Its staged decoy
# (hooks/*) is what a hook resolving its own location would see.
foreign_host() {
  local d; d=$(mktemp -d)
  _CLEANUP_DIRS+=("$d")
  git -C "$d" init -q -b main 2>/dev/null || git -C "$d" init -q
  git -C "$d" config user.email test@test
  git -C "$d" config user.name test
  mkdir -p "$d/hooks"
  cp -R "$ROOT/hooks/lib" "$d/hooks/"
  cp "$ROOT/hooks/$H" "$d/hooks/"
  printf 'decoy\n' > "$d/hooks/decoy-gate-tripper.sh"
  git -C "$d" add -f hooks/decoy-gate-tripper.sh
  echo "$d"
}
# run_from <project> <host> <json> [VAR=val ...] — hook lives in <host>; CWD is <project>.
run_from() {
  local proj="$1" host="$2" json="$3"; shift 3
  OUT=$(cd "$proj" && printf '%s' "$json" | env "$@" bash "$host/hooks/$H" 2>&1); RC=$?
}

t "no resolvable project root → BLOCKS rather than guessing"
host=$(foreign_host); outside=$(mktemp -d); _CLEANUP_DIRS+=("$outside")
run_from "$outside" "$host" "$COMMIT_JSON"
assert_rc_contains 2 "cannot determine the project root"

t "hook hosted in a foreign git repo still allows a clean project commit"
proj=$(new_repo); host=$(foreign_host)
stage "$proj" "README.md" "harmless"
run_from "$proj" "$host" "$COMMIT_JSON"
assert_rc 0

# ── check_plan_scope: staged paths vs the active PLAN.md <files> set ────────
# make_plan <repo> <status> <files-csv>
make_plan() {
  mkdir -p "$1/specs/demo"
  cat > "$1/specs/demo/PLAN.md" <<EOF
---
status: $2
---
\`\`\`xml
<task id="1.1"><files>$3</files><action>x</action></task>
\`\`\`
EOF
}

t "plan scope: no PLAN.md present → no scope note"
repo=$(new_repo $H)
stage "$repo" "app/foo.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"

t "plan scope: PLAN.md is SHIPPED (none active) → no note, even out-of-scope"
repo=$(new_repo $H)
make_plan "$repo" shipped "app/foo.py"
stage "$repo" "app/rogue.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"

t "plan scope: PLAN.md is PROPOSED (not yet active) → no note, even out-of-scope"
repo=$(new_repo $H)
make_plan "$repo" proposed "app/foo.py"
stage "$repo" "app/rogue.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"

t "plan scope: staged file in the active plan's <files> → no note"
repo=$(new_repo $H)
make_plan "$repo" active "app/foo.py, app/bar.py"
stage "$repo" "app/foo.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"

t "plan scope: staged file outside <files> → warn, exit 0"
repo=$(new_repo $H)
make_plan "$repo" active "app/foo.py"
stage "$repo" "app/rogue.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "blast-radius"

t "plan scope: same out-of-scope commit with BLAST_RADIUS_STRICT=1 → exit 2"
repo=$(new_repo $H)
make_plan "$repo" active "app/foo.py"
stage "$repo" "app/rogue.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON" BLAST_RADIUS_STRICT=1
assert_rc_contains 2 "outside the active plan"

t "plan scope: bookkeeping file (.md) is never flagged"
repo=$(new_repo $H)
make_plan "$repo" active "app/foo.py"
stage "$repo" "notes.md" "notes"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"

t "plan scope: basename match counts as in-scope (lenient/advisory)"
repo=$(new_repo $H)
make_plan "$repo" active "app/services/foo.py"
stage "$repo" "app/other/foo.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"

# make_md_plan <repo> <status> <files-csv> — markdown task syntax (plan-format.md two-syntaxes)
make_md_plan() {
  mkdir -p "$1/specs/mddemo"
  cat > "$1/specs/mddemo/PLAN.md" <<EOF
---
status: $2
---
### Task 1.1 — demo (wave 1)

- **Files:** $3
- **Action:** x
- **Verify:** \`true\`
- **Done:** ok
EOF
}

t "plan scope: markdown plan, staged file in the - **Files:** set → no note"
repo=$(new_repo $H)
make_md_plan "$repo" active "app/foo.py, app/bar.py"
stage "$repo" "app/foo.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"

t "plan scope: markdown plan, staged file outside the - **Files:** set → warn"
repo=$(new_repo $H)
make_md_plan "$repo" active "app/foo.py"
stage "$repo" "app/rogue.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "blast-radius"

t "plan scope: mixed plan, XML <files> and markdown - **Files:** sets are unioned"
repo=$(new_repo $H)
mkdir -p "$repo/specs/mixed"
cat > "$repo/specs/mixed/PLAN.md" <<'EOF'
---
status: active
---
```xml
<task id="1.1"><files>app/xml_task.py</files><action>x</action></task>
```

### Task 2.1 — md task (wave 2)

- **Files:** app/md_task.py
- **Action:** y
- **Verify:** `true`
- **Done:** ok
EOF
stage "$repo" "app/xml_task.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"
git -C "$repo" reset -q
stage "$repo" "app/md_task.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"

# make_plan_at <repo> <specdir> <status> <files-csv>
make_plan_at() {
  mkdir -p "$1/specs/$2"
  cat > "$1/specs/$2/PLAN.md" <<EOF
---
status: $3
---
\`\`\`xml
<task id="1.1"><files>$4</files><action>x</action></task>
\`\`\`
EOF
}

t "plan scope: multiple PLAN.md files, none active → no note even out-of-scope"
repo=$(new_repo $H)
make_plan_at "$repo" alpha shipped  "app/foo.py"
make_plan_at "$repo" beta  proposed "app/bar.py"
make_plan_at "$repo" gamma shipped  "app/baz.py"
stage "$repo" "app/rogue.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"

t "plan scope: exactly one active plan among many → its <files> set is enforced (warns)"
repo=$(new_repo $H)
make_plan_at "$repo" alpha shipped "app/old.py"
make_plan_at "$repo" beta  active  "app/foo.py"
make_plan_at "$repo" gamma shipped "app/other.py"
stage "$repo" "app/rogue.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_contains 0 "blast-radius"

t "plan scope: in-scope commit against the one active plan among many → no note"
repo=$(new_repo $H)
make_plan_at "$repo" alpha shipped "app/old.py"
make_plan_at "$repo" beta  active  "app/foo.py"
make_plan_at "$repo" gamma shipped "app/other.py"
stage "$repo" "app/foo.py" "x = 1"
run_hook "$repo" $H "$COMMIT_JSON"
assert_rc_not_contains 0 "blast-radius"

t "plan scope: multi-file commit reports every out-of-plan path once"
repo=$(new_repo $H)
make_plan "$repo" active "app/in.py"
stage "$repo" "app/out-a.py" "x = 1"
stage "$repo" "app/out-b.py" "x = 2"
run_hook "$repo" $H "$COMMIT_JSON"
if [ "$RC" -eq 0 ] && [ "$(printf '%s' "$OUT" | grep -o 'app/out-a.py' | wc -l | tr -d ' ')" = 1 ] && printf '%s' "$OUT" | grep -q 'app/out-b.py'; then pass
else fail "multi-path output was missing or duplicated: $OUT"; fi

# ── Profiles ──────────────────────────────────────────────────────────────
LANE_NORMAL_BAD=$'Lane: normal\nConfidence: high\nReason: a real filled reason\n\n### Verify\n\n| Check | Command | Exit | Notes |\n| --- | --- | --- | --- |\n| p | `<command>` | 0 | placeholder only |\n'

t "minimal: a staged secret still blocks"
repo=$(new_repo $H)
stage "$repo" "config.py" 'api_key = "supersecret12345"'
run_hook_args "$repo" $H "$COMMIT_JSON" --profile minimal
assert_rc_contains 2 "Potential secrets"

t "minimal: a SUMMARY lacking lane evidence is allowed (check_lane_evidence not run)"
repo=$(new_repo $H)
mkdir -p "$repo/scripts"; cp "$VERIFY_PY" "$repo/scripts/"
stage "$repo" "specs/demo/SUMMARY.md" "$LANE_NORMAL_BAD"
run_hook_args "$repo" $H "$COMMIT_JSON" --profile minimal
assert_rc_not_contains 0 "Lane evidence"

t "standard: the same SUMMARY is blocked (contrast for the minimal case)"
run_hook_args "$repo" $H "$COMMIT_JSON" --profile standard
assert_rc_contains 2 "Lane evidence... FAILED"

t "minimal: a hard-gate signal under a low Lane is allowed (check_risk not run)"
repo=$(new_repo $H)
stage "$repo" "hooks/real.sh" "echo real"
stage "$repo" "specs/demo/SUMMARY.md" "Lane: normal"
run_hook_args "$repo" $H "$COMMIT_JSON" --profile minimal
assert_rc_not_contains 0 "RISK CORROBORATION"

t "standard: an untracked .py does not deny a commit"
repo=$(new_repo $H)
printf 'x\n' > "$repo/loose.py"
run_hook_args "$repo" $H "$COMMIT_JSON" --profile standard
assert_rc_not_contains 0 "permissionDecision"

t "standard: an untracked .py does not deny a push"
run_hook_args "$repo" $H "$(json_bash 'git push origin main')" --profile standard
assert_silent_ok

t "strict: an untracked .py denies a commit"
run_hook_args "$repo" $H "$COMMIT_JSON" --profile strict
assert_rc_contains 0 '"permissionDecision":"deny"'

t "strict: an untracked .py denies a push"
run_hook_args "$repo" $H "$(json_bash 'git push origin main')" --profile strict
assert_rc_contains 0 '"permissionDecision":"deny"'

t "--profile=strict (equals form) is accepted"
run_hook_args "$repo" $H "$COMMIT_JSON" --profile=strict
assert_rc_contains 0 '"permissionDecision":"deny"'

t "unknown --profile warns and behaves as standard"
run_hook_args "$repo" $H "$COMMIT_JSON" --profile bogus
if [ "$RC" -eq 0 ] && echo "$OUT" | grep -qF "unknown --profile 'bogus'" \
  && ! echo "$OUT" | grep -qF permissionDecision && echo "$OUT" | grep -qF "App checks"; then pass
else fail "rc=$RC out: $(echo "$OUT" | head -4 | tr '\n' ' ')"; fi

t "strict: a hard-gate signal with no declared Lane blocks"
repo=$(new_repo $H)
stage "$repo" "hooks/real.sh" "echo real"
run_hook_args "$repo" $H "$COMMIT_JSON" --profile strict
assert_rc_contains 2 "strict, no Lane declared"

t "standard: the same signal with no declared Lane only warns"
run_hook_args "$repo" $H "$COMMIT_JSON" --profile standard
assert_rc_contains 0 "WARNING — hard-gate signals with no declared Lane"

t "strict: app gates run without REQUIRE_APP_GATES (breakpoint() blocks)"
repo=$(new_repo $H)
stage "$repo" "app/services/calc.py" 'breakpoint()'
run_hook_args "$repo" $H "$COMMIT_JSON" --profile strict
assert_rc_contains 2 "breakpoint"

finish
