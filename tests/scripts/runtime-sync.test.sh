#!/bin/bash
# Tests for deploy-harness.sh syncing/pruning the runtime/ directory (Phase B, GitHub issue #129).
# Mirrors tests/scripts/deploy-prune.test.sh's pattern, scoped to runtime/ instead of skills/.
source "$(dirname "$0")/../lib.sh"

DEPLOY="$ROOT/scripts/deploy-harness.sh"
new_target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); echo "$d"; }
deploy() { bash "$DEPLOY" --target "$1" </dev/null >/dev/null 2>&1; }

t "first deploy writes .harness-deployed and syncs runtime/"
T=$(new_target); deploy "$T"
if [ -f "$T/.claude/.harness-deployed" ] && [ -f "$T/.claude/runtime/run_state.py" ]; then pass
else fail "manifest missing or runtime/run_state.py did not land on first deploy"; fi

t "a runtime entry gone from source (in the prior manifest) is pruned on re-sync"
T=$(new_target); deploy "$T"
echo "runtime/_ghost.py" >> "$T/.claude/.harness-deployed"
touch "$T/.claude/runtime/_ghost.py"
deploy "$T"
if [ ! -e "$T/.claude/runtime/_ghost.py" ]; then pass; else fail "orphan runtime/_ghost.py was not pruned"; fi

t "a consumer's own file under runtime/ (never in the manifest) SURVIVES a re-sync"
T=$(new_target); deploy "$T"
touch "$T/.claude/runtime/consumer-custom.py"
deploy "$T"
if [ -f "$T/.claude/runtime/consumer-custom.py" ]; then pass
else fail "consumer's custom runtime/ file was destroyed — blind prune hazard"; fi

t "sidecars under runtime/ are never pruned"
T=$(new_target); deploy "$T"
touch "$T/.claude/runtime/run_state.py.harness-incoming"
deploy "$T"
if [ -e "$T/.claude/runtime/run_state.py.harness-incoming" ]; then pass
else fail "a sidecar under runtime/ was pruned"; fi

t "re-sync with no deletions prunes nothing under runtime/ (idempotent)"
T=$(new_target); deploy "$T"
before=$(find "$T/.claude/runtime" -maxdepth 1 | sort)
deploy "$T"
after=$(find "$T/.claude/runtime" -maxdepth 1 | sort)
if [ "$before" = "$after" ]; then pass; else fail "runtime/ set changed on a no-op re-sync"; fi

t "dry-run reports a would-be prune under runtime/ but writes nothing"
T=$(new_target); deploy "$T"
echo "runtime/_ghost2.py" >> "$T/.claude/.harness-deployed"
touch "$T/.claude/runtime/_ghost2.py"
out=$(bash "$DEPLOY" --target "$T" --dry-run </dev/null 2>&1)
if printf '%s' "$out" | grep -qF "would prune stale" && [ -e "$T/.claude/runtime/_ghost2.py" ]; then pass
else fail "dry-run did not report, or it deleted: out=$(printf '%s' "$out" | grep -i prune | head -1)"; fi

finish
