#!/bin/bash
# Contract test: docs warn that a named workflow can be stale after a plugin update,
# give the scriptPath workaround, and tell the report to name the script that ran.
source "$(dirname "$0")/../lib.sh"

LA="$ROOT/plugins/harness/skills/autopilot/references/launch-args.md"
RD="$ROOT/README.md"
SHIPPATH='plugins/harness/workflows/ship.js'

for f in "$LA" "$RD"; do
  n=$(basename "$f")
  t "$n warns about a stale name (restart) and gives the scriptPath workaround with $SHIPPATH"
  if grep -qF 'scriptPath' "$f" && grep -qF "$SHIPPATH" "$f" && grep -qiE 'restart' "$f" && grep -qi 'stale' "$f"; then pass; else fail "$n missing stale/restart/scriptPath/ship.js"; fi
done

t "launch-args.md reads the 'Script file:' line and falls back to 'script path not shown'"
if grep -qF 'Script file:' "$LA" && grep -qF 'script path not shown' "$LA"; then pass; else fail "report rule"; fi
finish
