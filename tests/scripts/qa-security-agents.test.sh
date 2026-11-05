#!/usr/bin/env bash
# The QA writer and the security reviewer carry their limits in their frontmatter: neither can
# edit code or spawn agents, and the security reviewer cannot write at all. The prompt carries the
# blindness rules, so the test pins the words that state them.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
fm() { awk 'NR==1&&/^---$/{inb=1;next} inb&&/^---$/{exit} inb' "$1"; }

qa="$root/plugins/harness/agents/qa-writer.md"
fm_qa=$(fm "$qa")
printf '%s\n' "$fm_qa" | grep -q '^name: qa-writer$'
if printf '%s\n' "$fm_qa" | grep -E '^tools:.*(Edit|Agent|WebFetch|WebSearch|mcp__)'; then
  echo "qa-writer exposes a tool it does not need" >&2
  exit 1
fi
grep -q 'You must not read application source code' "$qa"
grep -q 'Add acceptance tests for #' "$qa"
grep -q 'Never push' "$qa"

sec="$root/plugins/harness/agents/security-reviewer.md"
fm_sec=$(fm "$sec")
printf '%s\n' "$fm_sec" | grep -q '^name: security-reviewer$'
printf '%s\n' "$fm_sec" | grep -q '^model: claude-opus-5-5$'
if printf '%s\n' "$fm_sec" | grep -E '^tools:.*(Write|Edit|Agent|WebFetch|WebSearch|mcp__)'; then
  echo "security-reviewer exposes a mutation-capable or network tool" >&2
  exit 1
fi
grep -q 'enforced by this prompt, not by a hook' "$sec"
echo 'qa-security-agents: passed'
