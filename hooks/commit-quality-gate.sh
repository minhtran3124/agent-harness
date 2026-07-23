#!/bin/bash
# PreToolUse hook: block git commit if secrets, debug artifacts, or test failures are found.
# Exits 0 to allow, exits 2 to block.
# No set -e: we handle errors explicitly to control flow.

# Parse the bash command from stdin JSON
INPUT=$(cat /dev/stdin)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Only gate git commit commands (tokenizing matcher — resists cd/&&/-C/-c bypass)
source "$(cd "$(dirname "$0")" && pwd)/lib/git-command.sh" 2>/dev/null
# Fail closed: if the matcher lib is missing, block rather than let commits through unscanned.
command -v hook_cmd_is_git_commit >/dev/null 2>&1 || {
  echo "[COMMIT GATE] git-command matcher lib missing — redeploy harness (blocking to fail safe)." >&2
  exit 2
}
hook_cmd_is_git_commit "$COMMAND" || exit 0

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
# Check 1.5: Pending escalations (deny-on-no-response, mechanized)
# ─────────────────────────────────────────────
# templates/ESCALATIONS.template.md declares deny-on-no-response; this makes it
# real (review 2026-07-16 finding C5: a spec shipped with decision: pending).
# Scope: block only commits that touch specs/<slug>/ for a slug whose
# ESCALATIONS.md still has a pending decision — recording the decision in the
# same commit unblocks (the staged copy is what gets checked).
ESC_SLUGS=$(git diff --cached --name-only 2>/dev/null \
  | grep -oE '^specs/[^/]+/' | sort -u || true)
for slug_dir in $ESC_SLUGS; do
  esc="${slug_dir}ESCALATIONS.md"
  # Prefer the staged copy (a commit recording the decision must self-unblock)
  esc_content=$(git show ":$esc" 2>/dev/null || cat "$esc" 2>/dev/null || true)
  [ -z "$esc_content" ] && continue
  if echo "$esc_content" | grep -qiE '^[-*]?[[:space:]]*decision:[[:space:]]*pending'; then
    echo "[COMMIT GATE] Escalations... FAILED" >&2
    echo "  BLOCKED: $esc has 'decision: pending' (deny-on-no-response)." >&2
    echo "  A human records the decision in that file (decision/decided_by/decided_at)," >&2
    echo "  then this commit unblocks. See rules/orchestration.md → Escalation decision." >&2
    exit 2
  fi
done
echo "[COMMIT GATE] Escalations... PASSED" >&2

# ─────────────────────────────────────────────
# Check 1.6: Lane evidence (mechanizes rules/auto-correct-scope.md)
# ─────────────────────────────────────────────
# rules/auto-correct-scope.md calls scripts/verify_summary.py --lane the single
# source of truth for the lane -> evidence mapping, but nothing originally invoked it
# (PR #119 review finding: the script was proven by unit tests and then never
# run against a real SUMMARY). This makes the mapping real.
# Scope mirrors Check 1.5: only commits touching specs/<slug>/, and the STAGED
# SUMMARY is what gets checked, so a commit that records the evidence
# self-unblocks. Fail-open when python3 is unavailable (a missing interpreter
# must not gate commits — same convention as Check 2.5's re-run).
EV_SLUGS=$(git diff --cached --name-only 2>/dev/null \
  | grep -oE '^specs/[^/]+/' | sort -u || true)
if [ -n "$EV_SLUGS" ]; then
  if command -v python3 >/dev/null 2>&1 && [ -f scripts/verify_summary.py ]; then
    EV_FAILED=0
    for slug_dir in $EV_SLUGS; do
      summary="${slug_dir}SUMMARY.md"
      # Prefer the staged copy; fall back to on-disk (slug touched but SUMMARY unstaged)
      ev_tmp=$(mktemp 2>/dev/null) || continue
      if ! git show ":$summary" >"$ev_tmp" 2>/dev/null; then
        if [ -f "$summary" ]; then
          cp "$summary" "$ev_tmp" 2>/dev/null || { rm -f "$ev_tmp"; continue; }
        else
          # No SUMMARY at all for this slug — not this check's business
          # (a slug dir can hold only PLAN.md/design.md).
          rm -f "$ev_tmp"; continue
        fi
      fi
      # Capture rather than stream: the script names the temp path, which would
      # be meaningless to the committer. Re-label it as the real SUMMARY.
      # --plan-dir points SC-coverage at the real spec dir: the SUMMARY content is
      # read from the mktemp copy, whose parent has no PLAN.md, so without this the
      # sibling-PLAN.md lookup (and thus SC coverage) would silently fail-open.
      if ! ev_out=$(python3 scripts/verify_summary.py --lane "$ev_tmp" --plan-dir "$slug_dir" 2>&1); then
        echo "${ev_out//$ev_tmp/$summary}" >&2
        EV_FAILED=1
      fi
      rm -f "$ev_tmp"
    done
    if [ "$EV_FAILED" = "1" ]; then
      echo "[COMMIT GATE] Lane evidence... FAILED" >&2
      echo "  BLOCKED: a staged SUMMARY.md is missing the evidence its Lane requires." >&2
      echo "  tiny -> Lane/Confidence/Reason filled; normal -> + a real ### Verify row;" >&2
      echo "  high-risk -> + a non-empty ### Rollback. See rules/auto-correct-scope.md." >&2
      exit 2
    fi
    echo "[COMMIT GATE] Lane evidence... PASSED" >&2
  else
    echo "[COMMIT GATE] Lane evidence skipped: python3 or scripts/verify_summary.py unavailable." >&2
  fi
fi

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

    # Re-run the ### Verify table so proof is machine-verified, not self-reported.
    # Degrade (warn, do not block) when python3 or the script is unavailable —
    # a missing interpreter must not gate commits (fail-open, like the `|| true`
    # convention elsewhere in this hook).
    SLUG=$(basename "$(dirname "$SUMMARY")")
    if command -v python3 >/dev/null 2>&1 && [[ -f scripts/verify_summary.py ]]; then
      if ! python3 scripts/verify_summary.py --check "$SLUG" >&2; then
        echo "[COMMIT GATE] Evidence (### Verify re-run)... FAILED" >&2
        echo "  BLOCKED: claimed Exit codes in $SUMMARY do not match a fresh run (see mismatch above)." >&2
        echo "  Fix the commands/exit codes in the ### Verify table, or unset REQUIRE_VERIFY." >&2
        exit 2
      fi
      echo "[COMMIT GATE] Evidence (### Verify re-run)... PASSED" >&2
    else
      echo "[COMMIT GATE] Evidence re-run skipped: python3 or scripts/verify_summary.py unavailable — presence check only." >&2
    fi
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
