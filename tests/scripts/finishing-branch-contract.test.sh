#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="plugins/harness/skills/finishing-a-development-branch/SKILL.md"

t "finishing keeps create-PR-only safety boundary"
grep -q 'Never merge, force-push' "$ROOT/$SKILL" && grep -q 'Stage' "$ROOT/$SKILL" && pass || fail "PR safety boundary missing"

t "finishing PR body has the required sections"
ok=1
for s in Summary Why Changes Decisions Testing Risk 'How to revert' Notes; do
  grep -qF "**$s**" "$ROOT/$SKILL" || { ok=0; echo "missing section: $s"; }
done
[ "$ok" = 1 ] && pass || fail "PR body section missing"

t "finishing verifies before it pushes"
awk '/Verify/{v=NR} /git push/{p=NR} END{exit !(v && p && v<p)}' "$ROOT/$SKILL" && pass || fail "verify step must come before push"

t "finishing no longer pins review receipts or run state"
! grep -q 'receipt\|run_state\|verify_summary\|RUN.json' "$ROOT/$SKILL" && pass || fail "retired machinery still referenced"

t "finishing has an Auto mode section"
grep -q '^## Auto mode' "$ROOT/$SKILL" && pass || fail "Auto mode section missing"
finish
