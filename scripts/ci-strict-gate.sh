#!/usr/bin/env bash
# CI strict gate — intended to run on pull_request events.
#
# When a PR diff touches hard-gate paths, it must carry proof: a CHANGED
# specs/*/SUMMARY.md that declares `Lane: high-risk` AND has at least one
# non-placeholder `### Verify` row, and that SUMMARY's checks must re-run clean
# (via scripts/verify_summary.py --check). Diffs that do NOT touch hard-gate
# paths pass silently.
#
# This is the "strict-in-CI-first" layer: the strict semantics live HERE, in the
# script — NOT in an env var. Local commit hooks keep their warn-by-default
# behaviour (REQUIRE_VERIFY / RISK_CORROBORATION_STRICT unset); CI is the
# official strict gate. Breakage data is read from CI history + the ledger before
# anyone considers flipping the local default.
#
# Usage: scripts/ci-strict-gate.sh [base-ref]   (default base: origin/main)
set -uo pipefail

BASE="${1:-origin/main}"

# Hard-gate path regex — reuse risk-corroboration.sh's fix-precision pattern. The
# `^hooks/` anchor deliberately EXCLUDES tests/hooks/ (the documented
# false-positive class), EXTENDED here with `^templates/`: the SUMMARY schema is
# machine-read by the ledger + risk-corroboration, so a template change is a
# contract change. The `^templates/` arm is an intentional CI-only extension and
# is NOT present in the local hook's pattern.
HARD_GATE_RE='(^|/)settings\.json$|^hooks/|(^|/)\.claude/hooks/|render_plan\.py$|^templates/'

DIFF=$(git diff --name-only "$BASE"...HEAD 2>/dev/null || true)
[ -z "$DIFF" ] && exit 0

if ! echo "$DIFF" | grep -qE "$HARD_GATE_RE"; then
  exit 0  # no hard-gate paths touched → nothing to corroborate
fi

echo "[ci-strict-gate] diff touches hard-gate paths — requiring a high-risk SUMMARY with machine-verified proof" >&2

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
  echo "  ✗ diff touches hard-gate paths but no changed specs/*/SUMMARY.md declares 'Lane: high-risk' with a non-placeholder ### Verify row" >&2
  echo "[ci-strict-gate] BLOCKED" >&2
  exit 1
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
echo "  ✗ no changed high-risk SUMMARY passed verify_summary --check (proof not machine-verified)" >&2
echo "[ci-strict-gate] BLOCKED" >&2
exit 1
