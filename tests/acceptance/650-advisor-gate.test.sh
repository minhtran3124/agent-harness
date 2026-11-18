#!/bin/bash
# Acceptance tests for #650: ship.js lets the advisor judge a failed ticket gate when the base is feat/*.
# The ship.js cases ga1-ga6 live in tests/workflows/harness.js (stub agent(), no real agents).
source "$(dirname "$0")/../lib.sh"

OUT=$(cd "$ROOT" && node tests/workflows/harness.js 2>/dev/null)

for pair in "AC1:ga1:leftover 55 on feat/x, accept gives done, 1 call, 1 body item" \
            "AC2:ga2:base main gives 0 advisor gate calls and blocked" \
            "AC3:ga3:verdict owner blocks with 'human merge: gate review failed'" \
            "AC4:ga4:verdict fix gives 1 more fix, 1 more review, no second advisor call" \
            "AC5:ga5:a failed CI gate gives 0 advisor gate calls" \
            "AC6:ga6:no accepted item gives no Accepted by advisor section"; do
  IFS=: read -r ac ga what <<< "$pair"
  t "$ac: $what"
  echo "$OUT" | grep -qE "^PASS $ga:" && pass || fail "no 'PASS $ga:' line from harness.js"
done

t "AC8: harness.js prints PASS for ga1-ga6 (grep -c prints 6)"
n=$(echo "$OUT" | grep -cE '^PASS ga[1-6]:')
[ "$n" = 6 ] && pass || fail "grep -c printed: $n"

t "AC7: the merge-guard hook test exits 0"
bash "$ROOT/tests/hooks/merge-guard.test.sh" >/dev/null 2>&1 && pass || fail "merge-guard.test.sh failed"

t "AC7: the merge-guard hook is unchanged against the main branch"
REF=""
for r in origin/main github/main main; do git -C "$ROOT" rev-parse --verify -q "$r" >/dev/null && { REF=$r; break; }; done
if [ -z "$REF" ]; then fail "no main ref found to compare merge-guard.sh against"
else
  d=$(git -C "$ROOT" diff --stat "$REF" -- plugins/harness/hooks/merge-guard.sh)
  [ -z "$d" ] && pass || fail "merge-guard.sh differs from $REF: $d"
fi

SHIP="$ROOT/plugins/harness/workflows/ship.js"

t "AC10: a gate-statement comment names feat/* and says what it does not verify"
grep -qiE '^\s*//.*does not verify' "$SHIP" && grep -qE '^\s*//.*feat/' "$SHIP" && pass || fail "no gate-statement comment with 'does not verify' in ship.js"

t "AC9: ship.js records accepted items as 'Accepted by advisor' decisions"
grep -q 'Accepted by advisor' "$SHIP" && grep -q 'advisor gate' "$SHIP" && pass || fail "ship.js lacks 'Accepted by advisor' or 'advisor gate'"

t "AC11: docs/workflows.md describes the advisor gate path"
grep -q 'Accepted by advisor' "$ROOT/docs/workflows.md" && pass || fail "docs/workflows.md has no 'Accepted by advisor'"

t "AC11: README.md merge policy mentions the advisor"
grep -iE 'merge' "$ROOT/README.md" | grep -qi 'advisor' && pass || fail "README merge policy line has no advisor sentence"

t "AC11: a new ADR 0037 exists"
ls "$ROOT"/docs/adr/0037-*.md >/dev/null 2>&1 && pass || fail "no docs/adr/0037-*.md"

t "AC8: scripts/run-tests.sh ends with ALL GREEN"
skip "run by the last stage (running it here would recurse into this file)"

finish
