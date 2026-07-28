#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="skills/finishing-a-development-branch/SKILL.md"

t "finishing resolves one deterministic context"
grep -q 'resolve_finish_context.py' "$ROOT/$SKILL" && grep -q 'reports ambiguity, ask the' "$ROOT/$SKILL" && pass || fail "resolver contract missing"

t "finishing requires receipt and audit gate for plan work"
grep -q 'check_review_receipt.py' "$ROOT/$SKILL" && grep -q -- '--require correctness,intent --require-audit-if' "$ROOT/$SKILL" && pass || fail "receipt gate missing"

t "finishing keeps create-PR-only safety boundary"
grep -q 'Never merge, force-push' "$ROOT/$SKILL" && grep -q 'Stage named' "$ROOT/$SKILL" && pass || fail "PR safety boundary missing"

finish
