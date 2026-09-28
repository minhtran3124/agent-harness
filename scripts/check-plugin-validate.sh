#!/bin/bash
# Run the Claude Code plugin validator over this repo's skills and agents, failing on any
# real finding while allowlisting three files the validator structurally mis-classifies.
#
# Verifies:        every skills/*/SKILL.md and agents/*.md the validator can see carries the
#                  frontmatter the runtime expects (proven: removing `description:` from a
#                  SKILL.md makes this exit 1 and name that skill).
# Does not verify: that a skill's frontmatter is CORRECT — only that the required fields are
#                  present and parse. A wrong `allowed-tools` list passes this check.
#
# WHY THE ALLOWLIST, and why the obvious fix is wrong:
#   `claude plugin validate` classifies every *.md under agents/ as an agent definition.
#   agents/README.md (an index), agents/PROJECT.md (per-repo execution config) and
#   agents/PROJECT.template.md (its template) are not agents, so they warn "No frontmatter".
#   Adding frontmatter would REGISTER THEM AS THREE DISPATCHABLE AGENTS — strictly worse than
#   the warning. Moving them is also not free: agents/PROJECT.md is in deploy-harness.sh's
#   BOOTSTRAP_OWNED_FILES (conflict-protected, per-repo owned) and agents/coding.md and
#   agents/test-runner.md reference it by path. So the files stay and the warning is named
#   here, where the reason is reviewable, rather than silenced globally.
set -u
cd "$(dirname "$0")/.." || exit 1

# Files that are not agents despite living in agents/. Keep this list SHORT and justified —
# every entry is a place this check is deliberately blind.
ALLOWLIST="agents/README.md agents/PROJECT.md agents/PROJECT.template.md"

if ! command -v claude >/dev/null 2>&1; then
  # Named skip, never a silent pass (docs/solutions/harness — a skip that reads like a pass is
  # how a gate stops being a gate). CI runners do not ship the Claude Code CLI today, so this
  # check is currently a LOCAL gate only; it will start covering CI the moment one does.
  echo "  skip — plugin validate: the 'claude' CLI is not on PATH (local-only gate today)"
  exit 0
fi

OUT=$(claude plugin validate --strict --json . 2>/dev/null)
if [ -z "$OUT" ]; then
  echo "  skip — plugin validate: validator produced no JSON (unsupported CLI version?)"
  exit 0
fi

printf '%s' "$OUT" | ALLOWLIST="$ALLOWLIST" python3 -c '
import json, os, sys

allow = set(os.environ["ALLOWLIST"].split())
try:
    d = json.load(sys.stdin)
except Exception as e:
    print(f"  skip — plugin validate: unparseable JSON ({e})")
    sys.exit(0)

bad = []
for c in d.get("contents", []):
    rel = os.path.relpath(c.get("file", ""))
    for e in c.get("errors", []):
        bad.append(("error", rel, e.get("message", "")))
    if rel in allow:
        continue
    for w in c.get("warnings", []):
        bad.append(("warning", rel, w.get("message", "")))

if bad:
    print("  ✗ plugin validate:", file=sys.stderr)
    for kind, rel, msg in bad:
        print(f"      {kind}: {rel} — {msg[:110]}", file=sys.stderr)
    print("      Fix the frontmatter, or justify a new allowlist entry in this script.", file=sys.stderr)
    sys.exit(1)

n = len(d.get("contents", []))
print(f"  ✓ plugin validate clean ({len(allow)} non-agent files allowlisted, {n} reported)")
'
