#!/bin/bash
# Acceptance tests for #653: an ADR file only for a decision made before implement.
# AC1-AC4 live in scripts/acceptance/test_write_adrs_late.py; AC5 is the ship.js case ad1 in
# tests/workflows/harness.js (stub agent(), no real agents).
source "$(dirname "$0")/../lib.sh"

t "AC1-AC4: the four late/early write_adrs tests pass"
PY="${TMPDIR:-/tmp}/harness-tests-venv/bin/python"; [ -x "$PY" ] || PY=python3
out=$(cd "$ROOT" && "$PY" -m pytest scripts/acceptance/test_write_adrs_late.py -q -p no:cacheprovider -k 'test_late_ or test_early_' 2>&1)
rc=$?
{ [ $rc = 0 ] && echo "$out" | grep -q '4 passed'; } && pass || fail "exit $rc: $(echo "$out" | tail -3)"

t "AC5: harness case ad1 (review-stage adr decision reaches the ADR input with stage review)"
OUT=$(cd "$ROOT" && node tests/workflows/harness.js 2>/dev/null)
echo "$OUT" | grep -qE "^PASS ad1:" && pass || fail "no 'PASS ad1:' line from harness.js"

t "AC6: docs/adr/README.md says 'before implement'"
n=$(grep -c 'before implement' "$ROOT/docs/adr/README.md" 2>/dev/null)
{ [ -n "$n" ] && [ "$n" -ge 1 ]; } && pass || fail "grep -c printed: ${n:-no file}"

t "AC7: scripts/run-tests.sh ends with ALL GREEN"
skip "run by the last stage (running it here would recurse into this file)"

finish
