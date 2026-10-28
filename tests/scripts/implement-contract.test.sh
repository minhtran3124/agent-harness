#!/usr/bin/env bash
# The implement skill (was subagent-driven-development) no longer dispatches a per-task reviewer.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
impl="$root/skills/implement/SKILL.md"
test -f "$impl"
! test -e "$root/skills/subagent-driven-development"
! test -e "$root/skills/implement/task-reviewer-prompt.md"
! grep -q 'task-reviewer' "$impl"
grep -q '3 rounds' "$impl"
grep -q '^## Auto mode' "$impl"
echo 'sdd-task-review-routing: passed'
