#!/bin/bash
# Acceptance tests for #321 step 1: the tier-boundary sentence in step 2 of the brainstorming skill.
source "$(dirname "$0")/../lib.sh"

SK=plugins/harness/skills/brainstorming/SKILL.md
PHRASE='Do not ask how to implement or test'

# step2: the text of step 2 (from the "2. " line to the line before "3. ")
step2() { awk '/^2\. /{p=1} /^3\. /{p=0} p' "$ROOT/$SK"; }

t "AC1: the phrase appears on exactly one line"
n=$(grep -c "$PHRASE" "$ROOT/$SK")
[ "$n" -eq 1 ] && pass || fail "found $n lines"

t "AC1: that line is inside step 2"
step2 | grep -q "$PHRASE" && pass || fail "phrase not inside step 2"

t "AC1: step 2 still points approach choice to steps 3 and 4"
step2 | grep -q 'steps 3 and 4' && pass || fail "step 2 does not say 'steps 3 and 4'"

t "AC2: SKILL.md stays under 600 words"
w=$(wc -w < "$ROOT/$SK")
[ "$w" -lt 600 ] && pass || fail "$w words"

t "AC3: step 2 sentences are short (20 words or fewer)"
long=$(step2 | tr '\n' ' ' | sed 's/^2\. //' | sed 's/\([.?!]\) /\1\n/g' | awk 'NF>20{print NF": "$0}')
[ -z "$long" ] && pass || fail "long sentence: $long"

t "AC3: step 2 has no hedging words"
h=$(step2 | grep -Eiw 'might|may|could|perhaps|possibly|probably|usually|generally|try to|consider|should probably|maybe|ideally' )
[ -z "$h" ] && pass || fail "hedge: $h"

t "AC3: STE lint hard count of the skill is not above its baseline"
out=$(cd "$ROOT" && python3 scripts/check_ste_baseline.py 2>&1)
grep -q "$PHRASE" "$ROOT/$SK" && ! printf '%s\n' "$out" | grep -q "^WARN $SK" && pass || fail "phrase missing or lint worse: $(printf '%s\n' "$out" | grep "$SK")"

t "AC4: no file changes outside SKILL.md and the acceptance tests"
base=$(cd "$ROOT" && git log --format=%H --grep='^Add acceptance tests for #321$' -n1)
if [ -z "$base" ]; then fail "base commit 'Add acceptance tests for #321' not found"; else
  changed=$(cd "$ROOT" && { git diff --name-only "$base"; git ls-files --others --exclude-standard; } | sort -u | grep -v -e "^$SK\$" -e '^tests/acceptance/')
  [ -z "$changed" ] && pass || fail "other files changed: $changed"
fi

t "AC4: step 1 only, the other steps of SKILL.md are unchanged"
if [ -z "$base" ]; then fail "base commit not found"; else
  a=$(cd "$ROOT" && git show "$base:$SK" | awk '/^3\. /{p=1} p')
  b=$(awk '/^3\. /{p=1} p' "$ROOT/$SK")
  [ -n "$a" ] && [ "$a" = "$b" ] && pass || fail "text from step 3 on changed"
fi

t "AC5: scripts/run-tests.sh ends with ALL GREEN"
if [ -n "${HARNESS_ACCEPTANCE_NESTED:-}" ]; then skip "nested run"; else
  out=$(cd "$ROOT" && HARNESS_ACCEPTANCE_NESTED=1 bash scripts/run-tests.sh 2>&1); rc=$?
  [ "$rc" -eq 0 ] && printf '%s\n' "$out" | tail -5 | grep -q 'ALL GREEN' && pass || fail "rc=$rc; tail: $(printf '%s\n' "$out" | tail -3)"
fi
finish
