#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
brief="$tmp/task brief.md"
python3 "$root/skills/subagent-driven-development/scripts/task_brief.py" --plan "$root/specs/superpowers-6-review-pipeline-adoption/PLAN.md" --task 2.2 --output "$brief" >/dev/null
grep -q 'Task brief: 2.2' "$brief"
base=$(git -C "$root" rev-parse HEAD)
python3 "$root/skills/subagent-driven-development/scripts/review_package.py" --base "$base" --head "$base" --output "$tmp/package.md" >/dev/null
grep -q "BASE_SHA: $base" "$tmp/package.md"
if python3 "$root/skills/subagent-driven-development/scripts/review_package.py" --base not-a-sha --head "$base" --output "$tmp/bad" >/dev/null 2>&1; then exit 1; fi
sdd="$root/skills/subagent-driven-development"
grep -qF 'do not write a report file' "$sdd/implementer-prompt.md"
if grep -qF '[IMPLEMENTER_REPORT_PATH]' "$sdd/implementer-prompt.md"; then exit 1; fi
grep -qF 'the controller writes it verbatim to' "$sdd/SKILL.md"
grep -qF 'report-<task>.md' "$sdd/SKILL.md"
if grep -qF 'the full contract goes in the report file' "$root/rules/orchestration.md"; then exit 1; fi
echo 'sdd-artifact-handoffs: passed'
