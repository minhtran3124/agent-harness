#!/bin/bash
source "$(dirname "$0")/../lib.sh"
SKILL="skills/writing-plans/SKILL.md"
t "writing-plans explicitly loads canonical format rule"
grep -q 'Read `rules/plan-format.md`' "$ROOT/$SKILL" && pass || fail "format read missing"
t "writing-plans requires design and research brief"
grep -q 'design.md' "$ROOT/$SKILL" && grep -q 'research-brief.md' "$ROOT/$SKILL" && pass || fail "inputs missing"
t "writing-plans preserves worktree then SDD handoff"
grep -q 'using-git-worktrees' "$ROOT/$SKILL" && grep -q 'subagent-driven-development' "$ROOT/$SKILL" && pass || fail "handoff missing"
finish
