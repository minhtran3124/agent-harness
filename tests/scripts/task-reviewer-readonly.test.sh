#!/usr/bin/env bash
# The task reviewer is read-only by construction: its frontmatter lists only read tools, so the
# runtime, not the prompt, keeps it from writing. Model and tools live in the agent file itself.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
agent="$root/plugins/harness/agents/task-reviewer.md"

fm=$(awk 'NR==1&&/^---$/{inb=1;next} inb&&/^---$/{exit} inb' "$agent")
printf '%s\n' "$fm" | grep -q '^tools: Glob, Grep, Read$'
if printf '%s\n' "$fm" | grep -E '^tools:.*(Write|Edit|Agent|Bash|WebFetch|WebSearch|mcp__)'; then
  echo "task reviewer exposes a mutation-capable or network tool" >&2
  exit 1
fi
printf '%s\n' "$fm" | grep -q '^model: claude-opus-5-5$'
grep -q 'cannot write, edit, spawn agents' "$agent"
echo 'task-reviewer-readonly: passed'
