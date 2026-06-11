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
if [ "$FAILED" -eq 0 ]; then
  echo "ALL GREEN"
else
  echo "FAILURES — see above"
fi
exit "$FAILED"
