#!/bin/bash
# Run the Claude Code plugin validator, in strict mode, over the plugin and the marketplace.
#
# Verifies:        `claude plugin validate --strict` exits 0 for plugins/harness (manifest,
#                  skills, agents, hooks.json) and for the repo root (marketplace.json). Strict
#                  mode turns a warning, such as a skill with no frontmatter, into a failure.
# Does not verify: that a skill's frontmatter is CORRECT, only that it parses; or that the
#                  plugin loads in a live session (hooks firing, the Agents count after install).
#
# Skips by name, never silently, when the `claude` CLI is not on PATH, so a contributor without
# it is not blocked. CI sets REQUIRE_CLAUDE_CLI=1, which turns that skip into a failure: a gate
# that quietly vanishes when the install step breaks is no gate.
set -u
cd "$(dirname "$0")/.." || exit 1

if ! command -v claude >/dev/null 2>&1; then
  if [ "${REQUIRE_CLAUDE_CLI:-}" = 1 ]; then
    echo "  ✗ plugin validate: the 'claude' CLI is not on PATH and REQUIRE_CLAUDE_CLI=1" >&2
    exit 1
  fi
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
