#!/bin/bash
# Deploy places harness-manifest.json under .claude/ for consumer risk-mode parity.
source "$(dirname "$0")/../lib.sh"

t "deploy-harness copies harness-manifest.json into target .claude/"
src="$ROOT"
out=$(mktemp -d)
_CLEANUP_DIRS+=("$out")
# Minimal target: deploy into empty dir with --target
bash "$src/scripts/deploy-harness.sh" --target "$out" >/dev/null 2>&1
if [ -f "$out/.claude/harness-manifest.json" ]; then
  if jq -e '.hard_gates.detectable[] | select(.slug=="workflow-engine" and .mode=="warn")' \
    "$out/.claude/harness-manifest.json" >/dev/null 2>&1; then
    pass
  else
    fail "manifest present but workflow-engine not warn"
  fi
else
  fail "missing $out/.claude/harness-manifest.json"
fi

finish
