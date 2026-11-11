#!/usr/bin/env bash
# The QA verifier checks a ticket that has no app, blind to the plan and the diff. It cannot edit code
# or spawn agents (frontmatter). The blindness is a prompt rule, not a hook, so the test pins the words
# that state it and the gate statement.
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
fm() { awk 'NR==1&&/^---$/{inb=1;next} inb&&/^---$/{exit} inb' "$1"; }

f="$root/plugins/harness/agents/qa-verifier.md"
[ -f "$f" ] || { echo "missing $f" >&2; exit 1; }
fm_f=$(fm "$f")
printf '%s\n' "$fm_f" | grep -q '^name: qa-verifier$'
printf '%s\n' "$fm_f" | grep -q '^model: claude-sonnet-5-5$'
if printf '%s\n' "$fm_f" | grep -E '^tools:.*(Edit|Write|Agent|WebFetch|WebSearch|mcp__)'; then
  echo "qa-verifier exposes a tool it does not need" >&2
  exit 1
fi
for phrase in 'You must not read' 'Never fix code' 'Verifies:' 'Does not verify:'; do
  grep -q "$phrase" "$f" || { echo "qa-verifier.md lacks: $phrase" >&2; exit 1; }
done
echo 'qa-verifier-agent: passed'
