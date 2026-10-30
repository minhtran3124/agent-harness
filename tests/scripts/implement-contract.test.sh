#!/usr/bin/env bash
# The implement skill (was subagent-driven-development) no longer dispatches a per-task reviewer.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
impl="$root/plugins/harness/skills/implement/SKILL.md"
test -f "$impl"
! test -e "$root/plugins/harness/skills/subagent-driven-development"
! test -e "$root/plugins/harness/skills/implement/task-reviewer-prompt.md"
! grep -q 'task-reviewer' "$impl"
grep -q '3 rounds' "$impl"
grep -q '^## Auto mode' "$impl"
echo 'sdd-task-review-routing: passed'
