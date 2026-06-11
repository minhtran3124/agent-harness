#!/bin/bash
# Harness test entry point — run everything CI runs:
#   L1  syntax (bash -n) + doc-truth lint
#   L2  hook contract tests          (tests/hooks/*.test.sh)
#   L3  script integration tests     (tests/scripts/*.test.sh)
# Usage: bash scripts/run-tests.sh
set -u
cd "$(dirname "$0")/.." || exit 1
FAILED=0

echo "== L1: syntax =="
for f in hooks/*.sh scripts/*.sh tests/lib.sh tests/*/*.test.sh; do
  bash -n "$f" || { echo "  ✗ syntax: $f"; FAILED=1; }
done
echo "  ✓ bash -n clean"

echo "== L1: doc-truth lint =="
bash scripts/lint-doc-truth.sh || FAILED=1

for suite in tests/hooks/*.test.sh tests/scripts/*.test.sh; do
  echo ""
  echo "== $suite =="
  bash "$suite" || FAILED=1
done

echo ""
echo "== L2: python unit tests =="
# Prefer the shared venv lib.sh builds; else system python3; skip if pytest is unavailable.
PYBIN="${TMPDIR:-/tmp}/harness-tests-venv/bin/python"
[ -x "$PYBIN" ] || PYBIN="$(command -v python3 || true)"
if [ -n "$PYBIN" ] && "$PYBIN" -c 'import pytest' >/dev/null 2>&1; then
  # Engine unit tests that ship with the repo but nothing else runs.
  PYTESTS="scripts/test_check_plan_format.py skills/visual-planner/test_render_plan.py"
  # shellcheck disable=SC2086
  "$PYBIN" -m pytest $PYTESTS -q --no-header --no-cov -p no:cacheprovider || FAILED=1
else
  echo "  skip — no python3 with pytest available"
fi

echo ""
if [ "$FAILED" -eq 0 ]; then
  echo "ALL GREEN"
else
  echo "FAILURES — see above"
fi
exit "$FAILED"
