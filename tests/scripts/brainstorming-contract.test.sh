#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="skills/brainstorming/SKILL.md"
REF="skills/brainstorming/references/spec-review-loop.md"
t "brainstorming keeps the approval hard gate"
grep -q '<HARD-GATE>' "$ROOT/$SKILL" && grep -q 'Do not write code' "$ROOT/$SKILL" && pass || fail "approval gate missing"
t "brainstorming preserves xia2 then writing-plans handoff"
grep -q 'Invoke only `xia2`' "$ROOT/$SKILL" && grep -q '`writing-plans`' "$ROOT/$SKILL" && pass || fail "handoff missing"
t "review loop is conditionally referenced and exists"
grep -q 'references/spec-review-loop.md' "$ROOT/$SKILL" && [ -f "$ROOT/$REF" ] && pass || fail "review reference missing"
finish
