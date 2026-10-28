#!/bin/bash
# Deterministic tests for workflows/ship.js. A Node harness (tests/workflows/harness.js) loads the
# script with stubbed agent()/parallel()/phase()/log()/args, records every agent call and answers
# from a scripted table. No real agent runs. Each harness line "PASS <case>" / "FAIL <case>: why"
# becomes one case here.
source "$(dirname "$0")/../lib.sh"

t "ship.js tests (needs node)"
if ! command -v node >/dev/null 2>&1; then
  skip "node is not installed; the workflow harness is JavaScript"
  finish
fi

OUT=$(node "$ROOT/tests/workflows/harness.js" 2>&1); RC=$?
if [ -z "$OUT" ]; then
  fail "harness printed nothing (rc=$RC)"
fi
while IFS= read -r line; do
  case "$line" in
    "PASS "*) t "${line#PASS }"; pass ;;
    "FAIL "*) t "${line#FAIL }"; fail "see: node tests/workflows/harness.js" ;;
    "") ;;
    *) t "harness output"; fail "$line" ;;
  esac
done <<EOF
$OUT
EOF
if [ "$RC" -ne 0 ] && [ "$FAIL" -eq 0 ]; then t "harness exit code"; fail "rc=$RC"; fi
finish
