#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="skills/finishing-a-development-branch/SKILL.md"

t "finishing resolves one deterministic context"
grep -q 'resolve_finish_context.py' "$ROOT/$SKILL" && grep -q 'reports ambiguity, ask the' "$ROOT/$SKILL" && pass || fail "resolver contract missing"

t "finishing requires receipt, audit, and simplify gate for plan work"
grep -q 'check_review_receipt.py' "$ROOT/$SKILL" && grep -q -- '--require correctness,intent --require-audit-if <base> --require-simplify-if' "$ROOT/$SKILL" && pass || fail "receipt gate missing"

# tiny_simplify_gate_ok <dir> — 0 iff a tiny-lane plan still runs a standalone
# --require-simplify-if invocation (distinct from the non-tiny combined command),
# so an intake-mislabeled oversized-tiny diff cannot bypass the simplify gate.
tiny_simplify_gate_ok() {
  grep -q -- '<plan_dir> --require-simplify-if <base>' "$1/$SKILL"
}

t "finishing runs --require-simplify-if for tiny-lane plan work too, not just non-tiny"
if tiny_simplify_gate_ok "$ROOT"; then pass
else fail "no standalone --require-simplify-if invocation for tiny-lane plan work in $SKILL"; fi

t "finishing keeps create-PR-only safety boundary"
grep -q 'Never merge, force-push' "$ROOT/$SKILL" && grep -q 'Stage named' "$ROOT/$SKILL" && pass || fail "PR safety boundary missing"

# receipt_gate_ok <dir> → 0 iff the receipt-gate command line still requires the
# conditional simplify clause alongside the pre-existing audit clause.
receipt_gate_ok() {
  grep -q -- '--require correctness,intent --require-audit-if <base> --require-simplify-if' "$1/$SKILL"
}

t "mutation: removing --require-simplify-if from the receipt-gate command is detected"
m=$(mktemp -d); _CLEANUP_DIRS+=("$m")
cp -R "$ROOT/skills" "$m/skills"
sed -i.bak '/correctness,intent/ s/ --require-simplify-if <base>//' "$m/$SKILL" && rm -f "$m/$SKILL.bak"
if ! receipt_gate_ok "$m"; then pass
else fail "removing --require-simplify-if <base> was NOT detected — receipt_gate_ok still passed"; fi

t "mutation: removing the standalone tiny-lane simplify gate is detected"
m=$(mktemp -d); _CLEANUP_DIRS+=("$m")
cp -R "$ROOT/skills" "$m/skills"
sed -i.bak '/<plan_dir> --require-simplify-if <base>/d' "$m/$SKILL" && rm -f "$m/$SKILL.bak"
if ! tiny_simplify_gate_ok "$m"; then pass
else fail "removing the standalone tiny-lane invocation was NOT detected"; fi

finish
