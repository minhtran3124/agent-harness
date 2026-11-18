#!/bin/bash
# Acceptance tests for #651: REVIEW.md, and ship.js review stages read it from the base branch.
# The ship.js cases rv1-rv4 live in tests/workflows/harness.js (stub agent(), no real agents).
source "$(dirname "$0")/../lib.sh"

REVIEW="$ROOT/REVIEW.md"
SHIP="$ROOT/plugins/harness/workflows/ship.js"

t "AC1: REVIEW.md has exactly 4 '## ' sections"
n=$(grep -c '^## ' "$REVIEW" 2>/dev/null)
[ "$n" = 4 ] && pass || fail "grep -c printed: ${n:-no file}"

t "AC1: the four section names are present"
ok=1
for h in "What Important means here" "Cap the nits" "Do not report" "Always check"; do
  grep -qE "^## +$h" "$REVIEW" 2>/dev/null || { ok=0; echo "        missing: $h"; }
done
[ $ok = 1 ] && pass || fail "section heading missing"

t "AC2: table has 5 to 12 lines starting with '| '"
n=$(grep -c '^| ' "$REVIEW" 2>/dev/null)
{ [ -n "$n" ] && [ "$n" -ge 5 ] && [ "$n" -le 12 ]; } && pass || fail "grep -c printed: ${n:-no file}"

t "AC2: table columns are Trigger in the diff, Check, Source"
grep -E '^\| *Trigger in the diff *\| *Check *\| *Source *\|' "$REVIEW" >/dev/null 2>&1 && pass || fail "no header row with the three columns"

t "AC2: every Source path exists"
if [ ! -f "$REVIEW" ]; then fail "no REVIEW.md"
else
  bad=0; cnt=0
  while IFS= read -r line; do
    src=$(echo "$line" | awk -F'|' '{gsub(/^[ \t`]+|[ \t`]+$/,"",$(NF-1)); print $(NF-1)}')
    case "$src" in Source|---*|:--*|"") continue;; esac
    cnt=$((cnt+1))
    [ -f "$ROOT/$src" ] || { bad=1; echo "        missing: $src"; }
  done < <(grep '^| ' "$REVIEW")
  [ $bad = 0 ] && [ $cnt -ge 3 ] && pass || fail "bad path or fewer than 3 rows (rows: $cnt)"
fi

t "AC2: the three required Source paths are rows"
ok=1
for p in docs/solutions/scripts/bash-empty-array-and-jsonl-parsing-gotchas.md \
         docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md \
         docs/solutions/scripts/test-r-dev-tty-does-not-detect-missing-controlling-terminal.md; do
  grep '^| ' "$REVIEW" 2>/dev/null | grep -qF "$p" || { ok=0; echo "        missing row: $p"; }
done
[ $ok = 1 ] && pass || fail "required row missing"

t "AC2: no row about verify_summary or the commit gate"
if [ -f "$REVIEW" ] && ! grep '^| ' "$REVIEW" | grep -qiE 'verify_summary|commit gate'; then pass; else fail "REVIEW.md missing or has a removed-part row"; fi

OUT=$(cd "$ROOT" && node tests/workflows/harness.js 2>/dev/null)

for pair in "AC3:rv1:review prompt has 'show <base>:REVIEW.md'" \
            "AC4:rv2:review prompt has no worktree-path /REVIEW.md" \
            "AC5:rv3:gate review prompt reads REVIEW.md from the integration branch" \
            "AC6:rv4:fix-range re-review prompt carries the instruction"; do
  IFS=: read -r ac rv what <<< "$pair"
  t "$ac: $what"
  echo "$OUT" | grep -qE "^PASS $rv:" && pass || fail "no 'PASS $rv:' line from harness.js"
done

t "AC7: harness.js prints PASS for rv1-rv4 (grep -c prints 4)"
n=$(echo "$OUT" | grep -cE '^PASS rv[1-4]:')
[ "$n" = 4 ] && pass || fail "grep -c printed: $n"

t "AC8: ship.js names the log text 'review: no REVIEW.md on' and the 'REVIEW.md: ' summary prefix"
grep -qF 'review: no REVIEW.md on' "$SHIP" && grep -qF 'REVIEW.md: ' "$SHIP" && pass || fail "ship.js lacks the log text or the summary prefix"

t "AC8: ship.js prompt names the Do not report and Always check sections"
grep -qF 'Do not report' "$SHIP" && grep -qF 'Always check' "$SHIP" && pass || fail "ship.js prompt lacks a section name"

t "AC8: a gate-statement comment about REVIEW.md says what is not verified"
grep -E '^\s*//' "$SHIP" | grep -qE 'REVIEW\.md' && grep -E '^\s*//' "$SHIP" | grep -qiE 'does not verify' && pass || fail "no REVIEW.md gate-statement comment in ship.js"

t "AC9: docs/workflows.md review phase mentions REVIEW.md"
grep -qF 'REVIEW.md' "$ROOT/docs/workflows.md" && pass || fail "docs/workflows.md has no REVIEW.md"

t "AC9: CLAUDE.md Knowledge has a REVIEW.md line (no agent edit in a ticket PR, two PRs, owner approval)"
l=$(grep -F 'REVIEW.md' "$ROOT/CLAUDE.md")
if [ -n "$l" ] && echo "$l" | grep -qi 'two' && echo "$l" | grep -qi 'owner' && echo "$l" | grep -qiE 'never|not'; then pass; else fail "CLAUDE.md line missing or incomplete: $l"; fi

t "AC7: scripts/run-tests.sh ends with ALL GREEN"
skip "run by the last stage (running it here would recurse into this file)"

finish
