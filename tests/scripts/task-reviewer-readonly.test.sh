#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
agent="$root/agents/task-reviewer.md"
out=$(mktemp -d)
trap 'rm -rf "$out"' EXIT
python3 "$root/scripts/render_agent_definitions.py" \
  --root "$root" --runtime claude --output-dir "$out" >/dev/null
rendered="$out/task-reviewer.md"

# Semantic source is runtime-neutral; the Claude renderer owns the structural whitelist.
if rg -n '^(tools|model):' "$agent"; then
  echo "semantic task reviewer retains runtime policy" >&2
  exit 1
fi
grep -q '^tools: Glob, Grep, Read$' "$rendered"
if rg -n '^tools:.*(Write|Edit|Agent|Bash)' "$rendered"; then
  echo "rendered task reviewer exposes mutation-capable tool" >&2
  exit 1
fi
jq -e '.roles["task-reviewer"] | .filesystem == "read-only" and .nested_delegation == false and .mcp == "none" and .context_policy == "fresh-bounded"' \
  "$root/agents/agent-contracts.json" >/dev/null
grep -q 'cannot write, edit, spawn agents' "$agent"
echo 'task-reviewer-readonly: passed'
