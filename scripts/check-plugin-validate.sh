#!/bin/bash
# Run the Claude Code plugin validator, in strict mode, over the plugin and the marketplace.
#
# Verifies:        `claude plugin validate --strict` exits 0 for plugins/harness (manifest,
#                  skills, agents, hooks.json) and for the repo root (marketplace.json). Strict
#                  mode turns a warning, such as a skill with no frontmatter, into a failure.
# Does not verify: that a skill's frontmatter is CORRECT, only that it parses; or that the
#                  plugin loads in a live session (hooks firing, the Agents count after install).
#
# Skips by name, never silently, when the `claude` CLI is not on PATH. Runners that ship the CLI
# get the gate; today's GitHub runners do not.
set -u
cd "$(dirname "$0")/.." || exit 1

if ! command -v claude >/dev/null 2>&1; then
  echo "  skip — plugin validate: the 'claude' CLI is not on PATH (local-only gate today)"
  exit 0
fi

rc=0
for target in plugins/harness .; do
  if out=$(claude plugin validate "$target" --strict 2>&1); then
    echo "  ✓ plugin validate --strict $target"
  else
    rc=1
    echo "  ✗ plugin validate --strict $target" >&2
    printf '%s\n' "$out" | sed 's/^/      /' >&2
  fi
done
exit $rc
