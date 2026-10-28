#!/bin/bash
# Check that the plugin manifest version equals the root VERSION file.
#
# Verifies:        plugins/harness/.claude-plugin/plugin.json "version" == VERSION (trimmed).
# Does not verify: that either value is the right release number.
# scripts/bookkeeping.sh bumps both together; this catches a hand edit that moves only one.
# Usage: bash scripts/check-plugin-version.sh [--root DIR]
set -u
ROOT="."
[ "${1:-}" = "--root" ] && ROOT="${2:?--root needs a dir}"
cd "$ROOT" || exit 1
MANIFEST="plugins/harness/.claude-plugin/plugin.json"
[ -f VERSION ] || { echo "  ✗ plugin version: VERSION not found" >&2; exit 1; }
[ -f "$MANIFEST" ] || { echo "  ✗ plugin version: $MANIFEST not found" >&2; exit 1; }
want=$(tr -d '[:space:]' < VERSION)
# The "version" line is the only one that matches, so sed is enough (jq may be absent).
have=$(sed -n 's/^[[:space:]]*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$MANIFEST" | head -1)
if [ -n "$have" ] && [ "$have" = "$want" ]; then
  echo "  ✓ plugin.json version $have == VERSION"
else
  echo "  ✗ plugin.json version '${have:-<none>}' != VERSION '$want'" >&2
  exit 1
fi
