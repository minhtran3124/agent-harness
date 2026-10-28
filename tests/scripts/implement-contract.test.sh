#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
sdd="$root/skills/subagent-driven-development/SKILL.md"
grep -q 'cannot_verify.*one focused context' "$sdd"
grep -q 'Critical/Important' "$sdd"
grep -q 'Record Minor findings in SUMMARY' "$sdd"
grep -qi 'one reviewer returns both' "$sdd"
! test -e "$root/skills/subagent-driven-development/spec-reviewer-prompt.md"
! test -e "$root/skills/subagent-driven-development/code-quality-reviewer-prompt.md"
echo 'sdd-task-review-routing: passed'
