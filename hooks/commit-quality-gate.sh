#!/bin/bash
# PreToolUse hook: block git commit if secrets, debug artifacts, or test failures are found.
# Exits 0 to allow, exits 2 to block.
# No set -e: we handle errors explicitly to control flow.

# Parse the bash command from stdin JSON
INPUT=$(cat /dev/stdin)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Only gate git commit commands
if ! echo "$COMMAND" | grep -qE '^git commit'; then
  exit 0
fi

# Resolve the repo root (layout-independent; this repo is flat, hooks/ at top level)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
[ -z "$REPO_DIR" ] && REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"

# ─────────────────────────────────────────────
# Check 1: Secrets scan
# ─────────────────────────────────────────────
echo "[COMMIT GATE] Secrets scan..." >&2

# Get staged diff, exclude test files, examples, and docs
STAGED_DIFF=$(git diff --cached -U0 -- ':!tests/' ':!*.example' ':!*.md' ':!docs/' 2>/dev/null || true)

if echo "$STAGED_DIFF" | grep -qEi '(sk-[a-zA-Z0-9]{20,}|AKIA[0-9A-Z]{16}|password\s*=\s*["'"'"'][^"'"'"']+|passwd\s*=|api_key\s*=\s*["'"'"'][^"'"'"']+|apikey\s*=\s*["'"'"'][^"'"'"']+|client_secret\s*=\s*["'"'"'][^"'"'"']+|\bsecret\s*=\s*["'"'"'][^"'"'"']+)'; then
  echo "[COMMIT GATE] Secrets scan... FAILED" >&2
  echo "  BLOCKED: Potential secrets detected in staged changes." >&2
  echo "  Run 'git diff --cached' to review." >&2
  exit 2
fi

# Check for .env files staged
if git diff --cached --name-only 2>/dev/null | grep -qE '\.env$'; then
  echo "[COMMIT GATE] Secrets scan... FAILED" >&2
  echo "  BLOCKED: .env file staged for commit." >&2
  exit 2
fi

echo "[COMMIT GATE] Secrets scan... PASSED" >&2

# ─────────────────────────────────────────────
# Check 2: Debug artifacts in app/ code
# ─────────────────────────────────────────────
echo "[COMMIT GATE] Debug artifacts..." >&2

# Only check added lines (lines starting with +) in app/**/*.py
DEBUG_DIFF=$(git diff --cached -U0 -- 'app/**/*.py' 2>/dev/null || true)
ADDED_LINES=$(echo "$DEBUG_DIFF" | grep -E '^\+[^+]' || true)

if echo "$ADDED_LINES" | grep -qE '(breakpoint\(\)|import pdb|from pdb)'; then
  echo "[COMMIT GATE] Debug artifacts... FAILED" >&2
  echo "  BLOCKED: Found breakpoint()/pdb in staged app/ code." >&2
  exit 2
fi

# Check for bare print( — only lines that START with print( (after whitespace)
if echo "$ADDED_LINES" | grep -qE '^\+\s*print\('; then
  echo "[COMMIT GATE] Debug artifacts... FAILED" >&2
  echo "  BLOCKED: Found bare print() in staged app/ code." >&2
  echo "  Use logger instead, or remove debug prints." >&2
  exit 2
fi

echo "[COMMIT GATE] Debug artifacts... PASSED" >&2

# ─────────────────────────────────────────────
# Check 2.5: Evidence (### Verify) required for app/ changes (opt-in via REQUIRE_VERIFY=1)
# ─────────────────────────────────────────────
if [[ "${REQUIRE_VERIFY:-0}" == "1" ]]; then
  APP_STAGED=$(git diff --cached --name-only 2>/dev/null | grep -E '^app/.*\.py$' || true)
  if [[ -n "$APP_STAGED" ]]; then
    SUMMARY=$(git diff --cached --name-only 2>/dev/null | grep -E '(^|/)SUMMARY\.md$' | head -1)
    [[ -z "$SUMMARY" ]] && SUMMARY=$(ls -t specs/*/SUMMARY.md 2>/dev/null | head -1)
    if [[ -z "$SUMMARY" ]] || ! grep -qE '^### Verify' "$SUMMARY" 2>/dev/null; then
      echo "[COMMIT GATE] Evidence... FAILED" >&2
      echo "  BLOCKED: app/ changes staged but no '### Verify' block in specs/<slug>/SUMMARY.md." >&2
      echo "  Record the command(s) run + results (evidence over assertion), or unset REQUIRE_VERIFY." >&2
      exit 2
    fi
    echo "[COMMIT GATE] Evidence (### Verify present)... PASSED" >&2
  fi
fi

# ─────────────────────────────────────────────
# Check 3: Targeted tests for changed app/ files
# ─────────────────────────────────────────────

# Collect staged app/**/*.py files
CHANGED_APP_FILES=$(git diff --cached --name-only -- 'app/**/*.py' 2>/dev/null || true)

if [[ -z "$CHANGED_APP_FILES" ]]; then
  echo "[COMMIT GATE] No app/ Python files staged — skipping tests." >&2
  exit 0
fi

# Map app files to test files
TEST_FILES=""
FILE_COUNT=0

while IFS= read -r app_file; do
  [[ -z "$app_file" ]] && continue

  # Strip app/ prefix, get directory and filename
  relative="${app_file#app/}"
  dir_part=$(dirname "$relative")
  base_name=$(basename "$relative" .py)

  # Build candidate test paths (check nested first, then flattened)
  candidates=(
    "tests/${dir_part}/test_${base_name}.py"
    "tests/$(dirname "$dir_part")/test_${base_name}.py"
  )

  for candidate in "${candidates[@]}"; do
    if [[ -f "$candidate" ]]; then
      TEST_FILES="$TEST_FILES $candidate"
      FILE_COUNT=$((FILE_COUNT + 1))
      break
    fi
  done
done <<< "$CHANGED_APP_FILES"

if [[ -z "$TEST_FILES" ]]; then
  echo "[COMMIT GATE] No matching test files found — skipping tests." >&2
  exit 0
fi

echo "[COMMIT GATE] Running tests for $FILE_COUNT changed file(s)..." >&2

# Run pytest — no coverage, no integration tests, stop at first failure
# shellcheck disable=SC2086
OUTPUT=$(python -m pytest $TEST_FILES -x -q --tb=short --no-cov -m "not integration" -p no:cacheprovider 2>&1)
RESULT=$?

echo "$OUTPUT" | tail -20 >&2

if [[ $RESULT -ne 0 ]]; then
  echo "[COMMIT GATE] Tests... FAILED" >&2
  echo "  BLOCKED: Fix test failures before committing." >&2
  exit 2
fi

echo "[COMMIT GATE] Tests... PASSED" >&2

# ─────────────────────────────────────────────
# Hint: crystallization reminder
# ─────────────────────────────────────────────
STAGED_APP_COUNT=$(git diff --cached --name-only -- 'app/**/*.py' 2>/dev/null | wc -l | tr -d ' ')
if [[ "$STAGED_APP_COUNT" -ge 5 ]]; then
  echo "" >&2
  echo "  ★ Large session detected ($STAGED_APP_COUNT app/ files)." >&2
  echo "    Consider running /compound to crystallize learnings." >&2
  echo "" >&2
fi

exit 0
