#!/bin/bash
# Acceptance tests for #649: ship.js asks the advisor and retries when a stage is blocked (Opus, then Fable: owner, 2026-11-18).
# The ship.js cases rc1-rc5 live in tests/workflows/harness.js (stub agent(), no real agents).
source "$(dirname "$0")/../lib.sh"

OUT=$(cd "$ROOT" && node tests/workflows/harness.js 2>/dev/null)

for pair in "AC1:rc1:blocked then ok gives done, 1 recovery call, 2 stage calls" \
            "AC2:rc2:stays blocked gives blocked after an Opus and a Fable recovery (owner, 2026-11-18)" \
            "AC3:rc3:a blocked ticket leaves the independent ticket done" \
            "AC4:rc4:advisor verdict owner gives no retry and carries the reason" \
            "AC5:rc5:a dangerous decision gets no recovery call"; do
  IFS=: read -r ac rc what <<< "$pair"
  t "$ac: $what"
  echo "$OUT" | grep -qE "^PASS $rc:" && pass || fail "no 'PASS $rc:' line from harness.js"
done

t "AC7: harness.js prints PASS for rc1-rc5 (grep -c prints 5)"
n=$(echo "$OUT" | grep -cE '^PASS rc[1-5]:')
[ "$n" = 5 ] && pass || fail "grep -c printed: $n"

SHIP="$ROOT/plugins/harness/workflows/ship.js"

t "AC8: ship.js has a gate-statement comment above the recovery code"
grep -qiE '^\s*//\s*Gate: blocked-stage recovery' "$SHIP" && pass || fail "no 'Gate: blocked-stage recovery' comment"

t "AC8: ship.js names the advisor recovery stage and the fable model"
grep -q "'fable'" "$SHIP" && grep -q 'advisor recovery' "$SHIP" && pass || fail "no fable / advisor recovery in ship.js"

t "AC8: docs/workflows.md describes the advisor recovery"
grep -qi 'recovery' "$ROOT/docs/workflows.md" && pass || fail "docs/workflows.md has no 'recovery'"

t "AC8: CLAUDE.md 'Call the advisor when' list describes the blocked-stage recovery"
sed -n '/Call the advisor when/,/Workflow agents cannot/p' "$ROOT/CLAUDE.md" | grep -qi 'blocked stage\|returns blocked' && pass || fail "list has no blocked-stage item"

t "AC6: scripts/run-tests.sh ends with ALL GREEN"
skip "run by the last stage (running it here would recurse into this file)"

finish
