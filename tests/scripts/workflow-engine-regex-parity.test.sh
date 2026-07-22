#!/bin/bash
# The workflow-engine path signal exists in two enforcement points:
#   - hooks/risk-corroboration.sh   (commit-time lane gate: add_cat "workflow-engine")
#   - scripts/check_review_receipt.py (push-time gate: --require-audit-if)
# Both must recognise the SAME surfaces, or a change could clear one gate and trip
# the other. This test asserts the include + exclude patterns are byte-identical in
# both files — the drift guard that lets the duplicate copy stay honest (the same
# discipline as tests/scripts/inline-policy-drift.test.sh for policy prose).
source "$(dirname "$0")/../lib.sh"

HOOK="$ROOT/hooks/risk-corroboration.sh"
PY="$ROOT/scripts/check_review_receipt.py"

# The two canonical patterns (fixed strings — grep -F, no regex interpretation).
INCLUDE='^skills/[^/]+/SKILL\.md$|^skills/[^/]+/.*prompt[^/]*\.md$|^agents/[^/]+\.md$|^rules/[^/]+\.md$'
EXCLUDE='(^|/)(README\.md|[A-Za-z0-9_-]+\.template\.md)$'

t "workflow-engine INCLUDE pattern present in risk-corroboration.sh"
if grep -qF "$INCLUDE" "$HOOK"; then pass; else fail "hook missing include pattern"; fi

t "workflow-engine INCLUDE pattern present in check_review_receipt.py"
if grep -qF "$INCLUDE" "$PY"; then pass; else fail "python missing include pattern — DRIFT from hook"; fi

t "workflow-engine EXCLUDE pattern present in risk-corroboration.sh"
if grep -qF "$EXCLUDE" "$HOOK"; then pass; else fail "hook missing exclude pattern"; fi

t "workflow-engine EXCLUDE pattern present in check_review_receipt.py"
if grep -qF "$EXCLUDE" "$PY"; then pass; else fail "python missing exclude pattern — DRIFT from hook"; fi

t "mutation: a drifted python include pattern is detected"
m=$(mktemp -d); _CLEANUP_DIRS+=("$m")
sed 's#\^skills/\[\^/\]+/SKILL#^skills/[^/]+/DRIFTED#' "$PY" > "$m/py"
if grep -qF "$INCLUDE" "$m/py"; then fail "mutated copy still matched — grep -F not load-bearing"; else pass; fi

finish
