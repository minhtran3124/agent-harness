#!/usr/bin/env bash
# CI strict gate — intended to run on pull_request events.
#
# When a PR diff touches hard-gate paths, it must carry proof: a CHANGED
# specs/*/SUMMARY.md that declares `Lane: high-risk` AND has at least one
# non-placeholder `### Verify` row, and that SUMMARY's checks must re-run clean
# (via scripts/verify_summary.py --check). Diffs that do NOT touch a gated path
# pass silently.
#
# Two tiers:
#   BLOCK  hooks/, settings.json, templates/, render_plan.py  — missing proof exits 1
#   WARN   scripts/ (excluding scripts/test_*)                — missing proof exits 0
#          with a report; REQUIRE_SCRIPTS_PROOF=1 promotes it to BLOCK.
#
# Verifies:        that a PR touching a gated path carries >=1 re-run, exit-code-matched
#                  Verify row on a high-risk SUMMARY.
# Does not verify: that the Verify rows COVER the change. A PR can rewrite
#                  verify_summary.py and satisfy the gate with one unrelated passing
#                  row. Coverage is a judgment call left to human review.
#
# This is the "strict-in-CI-first" layer: the strict semantics live HERE, in the
# script — NOT in an env var. Local commit hooks keep their warn-by-default
# behaviour (REQUIRE_VERIFY / RISK_CORROBORATION_STRICT unset); CI is the
# official strict gate. Breakage data is read from CI history + the ledger before
# anyone considers flipping the local default.
#
# Usage: scripts/ci-strict-gate.sh [base-ref]
#   base-ref omitted → resolved by scripts/resolve-base-ref.sh; the gate SKIPS (exit 0,
#   named reason on stderr) when no base is declared. It never falls back to a guess.
set -uo pipefail

# The base must RESOLVE, whoever supplied it. `git diff <bad-ref>...HEAD 2>/dev/null || true`
# below swallows git's fatal, leaving DIFF empty, and an empty DIFF exits 0 — so an
# unresolvable base makes this STRICT gate report success having inspected nothing.
#
# Validating only the fallback is not enough, and was the bug an earlier draft of this
# block shipped: CI always passes the base explicitly (harness-ci.yml:
# `origin/${{ github.base_ref }}`), so the *only* path CI takes was the unvalidated one.
# `bash scripts/ci-strict-gate.sh no/such/ref` exited 0 with no output. Both paths are
# checked here; a bad base is a hard error, while a genuinely undeclared base is a skip.
if [ $# -ge 1 ]; then
  BASE="$1"
  if ! git rev-parse --verify -q "${BASE}^{commit}" >/dev/null 2>&1; then
    echo "ci-strict-gate: base ref '$BASE' does not resolve to a commit — refusing to" >&2
    echo "  report a result. An unresolvable base yields an empty diff, which this gate" >&2
    echo "  would otherwise read as 'nothing to check' and pass." >&2
    exit 1
  fi
elif BASE="$(bash "$(dirname "$0")/resolve-base-ref.sh" 2>&1)"; then
  :
else
  echo "ci-strict-gate: skipped — $BASE" >&2
  echo "ci-strict-gate: pass a base ref explicitly to run it (scripts/ci-strict-gate.sh <base>)" >&2
  exit 0
fi

# Hard-gate path regex — reuse commit-gate.sh check_risk's fix-precision pattern. The
# `^hooks/` anchor deliberately EXCLUDES tests/hooks/ (the documented
# false-positive class), EXTENDED here with `^templates/`: the SUMMARY schema is
# machine-read by the ledger + check_risk, so a template change is a
# contract change. The `^templates/` arm is an intentional CI-only extension and
# is NOT present in the local hook's pattern.
HARD_GATE_RE='(^|/)settings\.json$|^hooks/|(^|/)\.claude/hooks/|render_plan\.py$|^templates/'

# WARN-TIER path: `scripts/` holds the gate logic itself — scripts/verify_summary.py
# decides what every other gate accepts as evidence, yet was never re-run. Measured
# over the last 80 PRs: adding it catches 15 more PRs, of which 9 would block today.
# So it rolls out warn-first (same shape as REQUIRE_NOT_AUTO_VERIFIED), and
# REQUIRE_SCRIPTS_PROOF=1 promotes it to blocking.
#
# `scripts/test_*.py` is EXCLUDED: 21 of the 55 files under scripts/ are tests, and a
# test-only edit carries no production risk. This mirrors why `^hooks/` excludes
# tests/hooks/ — the documented false-positive class.
#
# `rules/` was surveyed and deliberately REJECTED: all 8 files are prose (no command's
# re-run proves a sentence correct), AND rules/*.md is already gated by the
# `workflow-engine` signal in commit-gate.sh check_risk + check_review_receipt.py, which
# demands a context-propagation audit — the right evidence shape for prose.
WARN_GATE_RE='^scripts/'
WARN_GATE_EXCLUDE_RE='^scripts/test_'

DIFF=$(git diff --name-only "$BASE"...HEAD 2>/dev/null || true)
[ -z "$DIFF" ] && exit 0

# SHIPPING SECTION — open-question check for every phase that ships in this PR. It sits
# BEFORE the tier selection because a specs-only PR flipping a PLAN.md to `shipped`
# touches no gated path and would take the early exit 0 below. It never exits 0 itself,
# so a PR that touches hooks/ and also ships a phase still needs high-risk proof.
# A slug ships when specs/<slug>/PLAN.md is in the diff and its frontmatter reads
# `status: shipped` at HEAD but not at the merge base (a missing file is not shipped),
# so an edit to an already-shipped plan, such as a status-log append, runs no check.
#
# Verifies:        a PR that ships a phase runs scripts/check_open_questions.py for it,
#                  and, under REQUIRE_QUESTIONS_CLOSED=1, fails when that check reports
#                  findings, errors (any exit other than 0 and 1), or is missing.
# Does not verify: a `status: shipped` committed outside a PR, or that a closed question
#                  was answered correctly (the check itself is traceability-tier).
plan_shipped() {  # stdin = PLAN.md; exit 0 when the frontmatter reads `status: shipped`
  # Reads ALL input: exiting at the closing `---` would SIGPIPE the `git show` feeding it,
  # and under pipefail a large plan would then read as not shipped. The status match
  # lowercases and drops leading whitespace, as render_plan.py does; a quoted value stays
  # unmatched there too.
  awk '{ sub(/\r$/, ""); sub(/[ \t]+$/, "") }
       done { next }
       $0 == "---" { n++; if (n == 2) done = 1; next }
       n == 1 { line = tolower($0); sub(/^[ \t]+/, "", line)
                if (line ~ /^status:[ \t]*shipped$/) found = 1 }
       END { exit !found }'
}
MERGE_BASE=$(git merge-base "$BASE" HEAD 2>/dev/null || true)
OQ_FAILED=0   # the check reported findings under REQUIRE_QUESTIONS_CLOSED=1
OQ_ERRORED=0  # the check itself failed (crash, usage error, missing interpreter)
OQ_MISSING=0  # scripts/check_open_questions.py is absent
OQ_REQUIRE="${REQUIRE_QUESTIONS_CLOSED:-0}"
# Quoting off for this list only: git quotes a non-ASCII path, which would miss the regex.
OQ_PLANS=$(git -c core.quotePath=false diff --name-only "$BASE"...HEAD 2>/dev/null \
  | grep -E '^specs/[^/]+/PLAN\.md$' || true)
while IFS= read -r plan; do
  [ -z "$plan" ] && continue
  git show "HEAD:$plan" 2>/dev/null | plan_shipped || continue
  [ -n "$MERGE_BASE" ] && git show "$MERGE_BASE:$plan" 2>/dev/null | plan_shipped && continue
  slug=$(basename "$(dirname "$plan")")
  if [ ! -f scripts/check_open_questions.py ]; then
    echo "open-question check skipped: scripts/check_open_questions.py not found" >&2
    OQ_MISSING=1
    continue
  fi
  echo "[ci-strict-gate] $slug ships in this diff — checking open questions" >&2
  python3 scripts/check_open_questions.py --slug "$slug"
  rc=$?
  # The script exits 1 only for findings under REQUIRE; a crash also exits 1, so an exit 1
  # without REQUIRE, or any other non-zero exit, is an error in the check, not a finding.
  if [ "$rc" -eq 1 ] && [ "$OQ_REQUIRE" = "1" ]; then
    OQ_FAILED=1
  elif [ "$rc" -ne 0 ]; then
    echo "open-question check errored for $slug (exit $rc)" >&2
    OQ_ERRORED=1
  fi
done <<< "$OQ_PLANS"
if [ "$OQ_REQUIRE" = "1" ]; then
  OQ_BLOCK=0
  if [ "$OQ_FAILED" = "1" ]; then
    echo "[ci-strict-gate] BLOCKED — open questions close at a shipping phase (REQUIRE_QUESTIONS_CLOSED=1)" >&2
    OQ_BLOCK=1
  fi
  if [ "$OQ_ERRORED" = "1" ]; then
    echo "[ci-strict-gate] BLOCKED — the open-question check errored (REQUIRE_QUESTIONS_CLOSED=1)" >&2
    OQ_BLOCK=1
  fi
  if [ "$OQ_MISSING" = "1" ]; then
    echo "[ci-strict-gate] BLOCKED — scripts/check_open_questions.py not found (REQUIRE_QUESTIONS_CLOSED=1)" >&2
    OQ_BLOCK=1
  fi
  [ "$OQ_BLOCK" = "1" ] && exit 1
fi

# MODE: block = a failure exits 1; warn = a failure is reported and exits 0.
if echo "$DIFF" | grep -qE "$HARD_GATE_RE"; then
  MODE=block
  echo "[ci-strict-gate] diff touches hard-gate paths — requiring a high-risk SUMMARY with machine-verified proof" >&2
elif echo "$DIFF" | grep -E "$WARN_GATE_RE" | grep -qvE "$WARN_GATE_EXCLUDE_RE"; then
  if [ "${REQUIRE_SCRIPTS_PROOF:-0}" = "1" ]; then
    MODE=block
    echo "[ci-strict-gate] diff touches scripts/ — REQUIRE_SCRIPTS_PROOF=1, enforcing" >&2
  else
    MODE=warn
    echo "[ci-strict-gate] diff touches scripts/ — checking for proof (WARN-ONLY rollout)" >&2
  fi
else
  exit 0  # no gated paths touched → nothing to corroborate
fi

# Report a gate failure, then exit per MODE. Warn mode must still SAY what is missing;
# a silent warn tier is indistinguishable from no gate at all.
gate_fail() {
  echo "  $1" >&2
  if [ "$MODE" = "warn" ]; then
    echo "[ci-strict-gate] WARN-ONLY — not blocking. Set REQUIRE_SCRIPTS_PROOF=1 to enforce." >&2
    exit 0
  fi
  echo "[ci-strict-gate] BLOCKED" >&2
  exit 1
}

CHANGED_SUMMARIES=$(echo "$DIFF" | grep -E '(^|/)specs/[^/]+/SUMMARY\.md$' || true)

QUALIFYING_SLUGS=""
while IFS= read -r s; do
  [ -z "$s" ] && continue
  [ -f "$s" ] || continue
  grep -qE '^Lane:[[:space:]]*high-risk' "$s" || continue
  # At least one non-placeholder ### Verify row — reuse the canonical parser so the
  # placeholder rules stay in one place (verify_summary.parse_verify_table).
  rows=$(python3 -c "
import sys
sys.path.insert(0, 'scripts')
from pathlib import Path
import verify_summary as v
print(len(v.parse_verify_table(Path(sys.argv[1]).read_text(encoding='utf-8'))))
" "$s" 2>/dev/null || echo 0)
  [ "${rows:-0}" -gt 0 ] || continue
  QUALIFYING_SLUGS="$QUALIFYING_SLUGS $(basename "$(dirname "$s")")"
done <<< "$CHANGED_SUMMARIES"

if [ -z "$QUALIFYING_SLUGS" ]; then
  gate_fail "✗ diff touches gated paths but no changed specs/*/SUMMARY.md declares 'Lane: high-risk' with a non-placeholder ### Verify row"
fi

# Re-run each qualifying slug's Verify table. The PR must carry proof: at least ONE
# changed high-risk SUMMARY must verify clean. A SUMMARY that fails --check is a
# non-blocking WARNING (e.g. a legacy table whose fixtures are gone) — the gate's
# guarantee is "this PR carries ≥1 piece of real, machine-verified proof", not that
# every SUMMARY touched in the diff re-runs (the first-ever specs/ commit makes the
# whole history "changed", which must not punish an honest change).
PASSED=0
for slug in $QUALIFYING_SLUGS; do
  if python3 scripts/verify_summary.py --check "$slug" >&2; then
    echo "  ✓ verified: $slug" >&2
    PASSED=$((PASSED + 1))
  else
    echo "  ⚠ warning: verify_summary --check did not pass for '$slug' (claimed vs actual mismatch above) — not blocking" >&2
  fi
done

if [ "$PASSED" -ge 1 ]; then
  echo "[ci-strict-gate] OK ($PASSED high-risk SUMMARY verified)" >&2
  exit 0
fi
gate_fail "✗ no changed high-risk SUMMARY passed verify_summary --check (proof not machine-verified)"
