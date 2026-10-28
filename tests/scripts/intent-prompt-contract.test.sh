#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="plugins/harness/skills/intent-review/SKILL.md"
AGENT="plugins/harness/agents/intent-reviewer.md"

t "intent review stops when the verbatim request is missing"
grep -q 'STOP and say so' "$ROOT/$SKILL" && grep -q 'Never reconstruct it' "$ROOT/$SKILL" && pass || fail "request stop gate missing"

t "intent reviewer remains plan-blind"
grep -q 'Never pass the plan' "$ROOT/$SKILL" && grep -q 'Do not read the plan' "$ROOT/$AGENT" && pass || fail "plan blindness missing"

t "skill dispatches the intent-reviewer agent with only the request and range"
grep -q 'Dispatch the `intent-reviewer` agent' "$ROOT/$SKILL" && grep -q 'only those two' "$ROOT/$SKILL" && pass || fail "dispatch contract missing"

t "gap drift excess taxonomy and verdict match between skill and agent"
for w in gap drift excess; do grep -q "\`$w\`" "$ROOT/$SKILL" && grep -q "^- $w:" "$ROOT/$AGENT" || fail "$w missing"; done
grep -q 'match | gaps found' "$ROOT/$SKILL" && grep -q 'match | gaps found' "$ROOT/$AGENT" && pass || fail "verdict missing"

finish
