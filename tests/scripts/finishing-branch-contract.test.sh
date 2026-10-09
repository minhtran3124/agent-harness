#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="skills/finishing-a-development-branch/SKILL.md"

t "finishing resolves one deterministic context"
grep -q 'resolve_finish_context.py' "$ROOT/$SKILL" && grep -q 'reports ambiguity, ask the' "$ROOT/$SKILL" && pass || fail "resolver contract missing"

t "finishing requires receipt and audit gate for plan work"
grep -q 'check_review_receipt.py' "$ROOT/$SKILL" && grep -q -- '--require correctness,intent --require-audit-if' "$ROOT/$SKILL" && pass || fail "receipt gate missing"

t "finishing keeps create-PR-only safety boundary"
grep -q 'Never merge, force-push' "$ROOT/$SKILL" && grep -q 'Stage named' "$ROOT/$SKILL" && pass || fail "PR safety boundary missing"

t "finishing emits the concrete ready_to_merge run-state producer (non-fatal)"
# The post-merge shipped transition is legal only from ready_to_merge; a prose-only checkpoint
# (as the slim refactor left it) lets a run stall at verifying. Guard the concrete command so a
# future prompt-slim pass cannot silently drop it again (issue #196).
grep -q -- '--to ready_to_merge --event pr.opened || true' "$ROOT/$SKILL" && pass || fail "concrete ready_to_merge transition (with || true) missing — a run would stall at verifying and never terminalize"

t "finishing runs the open-questions check before marking the plan shipped"
grep -qF 'python3 scripts/check_open_questions.py --slug <slug>' "$ROOT/$SKILL" && grep -qF 'Open questions closing here' "$ROOT/$SKILL" && pass || fail "open-questions check or PR-body list missing"

t "finishing runs the SC history check at step 3"
grep -qF 'python3 scripts/verify_summary.py --sc-history <slug> --base <base>' "$ROOT/$SKILL" && pass || fail "SC history check missing"

finish
