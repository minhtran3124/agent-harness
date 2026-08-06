#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
agent="$root/agents/task-reviewer.md"
grep -q '^tools: Glob, Grep, Read$' "$agent"
if rg -n '^tools:.*(Write|Edit|Agent|Bash)' "$agent"; then
  echo "task reviewer exposes mutation-capable tool" >&2
  exit 1
fi
grep -q 'cannot write, edit, spawn agents' "$agent"
echo 'task-reviewer-readonly: passed'
