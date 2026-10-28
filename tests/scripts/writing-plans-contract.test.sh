#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="skills/writing-plans/SKILL.md"
t "writing-plans reads design and research brief when they exist"
grep -q 'design.md' "$ROOT/$SKILL" && grep -q 'research-brief.md' "$ROOT/$SKILL" && pass || fail "inputs missing"
t "writing-plans steps carry Files, Effort, Done-when and a parallel group"
grep -q '\*\*Files\*\*' "$ROOT/$SKILL" && grep -q '\*\*Effort\*\*' "$ROOT/$SKILL" && grep -q '\*\*Done-when\*\*' "$ROOT/$SKILL" && grep -q '\*\*Parallel group\*\*' "$ROOT/$SKILL" && pass || fail "step fields missing"
t "writing-plans hands off to implement and drops the retired machinery"
grep -q '`implement`' "$ROOT/$SKILL" && ! grep -q 'check_plan_contract\|render_plan\|review-loop\|subagent-driven-development' "$ROOT/$SKILL" && pass || fail "handoff missing or retired machinery still referenced"
t "writing-plans has an Auto mode section"
grep -q '^## Auto mode' "$ROOT/$SKILL" && pass || fail "Auto mode section missing"
finish
