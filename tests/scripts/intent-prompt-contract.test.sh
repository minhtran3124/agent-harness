#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="skills/intent-review/SKILL.md"
PROMPT="skills/intent-review/intent-reviewer-prompt.md"

t "intent review retains the verbatim-intent stop gate"
grep -q 'verbatim primary oracle' "$ROOT/$SKILL" && grep -q 'ask the user instead of reconstructing' "$ROOT/$SKILL" && pass || fail "intent source gate missing"

t "intent reviewer remains plan-blind"
grep -q 'never `PLAN.md` prose' "$ROOT/$SKILL" && grep -qi 'must .*read.*PLAN.md\|do not read.*PLAN.md' "$ROOT/$PROMPT" && pass || fail "plan blindness missing"

t "all gap excess drift routes remain explicit"
grep -q '\*\*gap:\*\*' "$ROOT/$SKILL" && grep -q '\*\*drift:\*\*' "$ROOT/$SKILL" && grep -q '\*\*excess:\*\*' "$ROOT/$SKILL" && pass || fail "taxonomy missing"

finish
