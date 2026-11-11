#!/bin/bash
# Acceptance tests for #631: docs/research/watch-a-run-live.md, a short how-to for watching a run
# live on the board.
source "$(dirname "$0")/../lib.sh"

DOC="$ROOT/docs/research/watch-a-run-live.md"

t "AC1: the how-to exists and is under 40 lines"
if [ -f "$DOC" ]; then
  n=$(wc -l < "$DOC")
  [ "$n" -lt 40 ] && pass || fail "$n lines"
else fail "docs/research/watch-a-run-live.md is missing"; fi

t "AC2: names the board command and the address"
[ -f "$DOC" ] && grep -qF 'node plugins/harness/board/board.js' "$DOC" && grep -qF 'http://127.0.0.1:4317' "$DOC" && pass || fail "command or address missing"

t "AC3: says to start the board before or during /harness:autopilot"
[ -f "$DOC" ] && grep -qF '/harness:autopilot' "$DOC" && grep -Eqi 'before|during' "$DOC" && pass || fail "no autopilot start advice"

t "AC4: states the limit: log() lines and PR link appear only after the run ends"
[ -f "$DOC" ] && grep -qF 'log()' "$DOC" && grep -qi 'PR link' "$DOC" && grep -Eqi 'after the run|run ends|only after|once the run' "$DOC" && pass || fail "limit not stated"

t "AC5: scripts/run-tests.sh ends with ALL GREEN"
if [ -n "${HARNESS_ACCEPTANCE_NESTED:-}" ]; then skip "nested run"; else
  out=$(cd "$ROOT" && HARNESS_ACCEPTANCE_NESTED=1 bash scripts/run-tests.sh 2>&1); rc=$?
  [ "$rc" -eq 0 ] && printf '%s\n' "$out" | tail -5 | grep -q 'ALL GREEN' && pass || fail "rc=$rc; tail: $(printf '%s\n' "$out" | tail -3)"
fi
finish
