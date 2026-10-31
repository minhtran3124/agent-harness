#!/bin/bash
# xia2 tells the agent to run codegraph with CODEGRAPH_NO_DAEMON=1 CODEGRAPH_TELEMETRY=0 in front.
# A `Bash(codegraph explore *)` rule does not match a command with that prefix (measured: the
# command is denied), so the skill must grant the prefixed spelling too (#526).
source "$(dirname "$0")/../lib.sh"

SKILL="$(dirname "$0")/../../plugins/harness/skills/xia2/SKILL.md"
FM=$(awk 'NR==1&&/^---$/{inb=1;next} inb&&/^---$/{exit} inb' "$SKILL")
PFX='CODEGRAPH_NO_DAEMON=1 CODEGRAPH_TELEMETRY=0'

for sub in explore query callers callees; do
  t "xia2 allowed-tools grants the prefixed 'codegraph $sub' command"
  case "$FM" in
    *"Bash($PFX codegraph $sub *)"*) pass ;;
    *) fail "allowed-tools has no Bash($PFX codegraph $sub *)" ;;
  esac
done
finish
