#!/bin/bash
# Tests for deploy-harness.sh orphan pruning (deployed-manifest, safe by construction).
# The load-bearing case is "a consumer's own skill survives" — a blind prune would delete it.
source "$(dirname "$0")/../lib.sh"

DEPLOY="$ROOT/scripts/deploy-harness.sh"
new_target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); echo "$d"; }
deploy() { bash "$DEPLOY" --target "$1" </dev/null >/dev/null 2>&1; }

t "first deploy writes .harness-deployed and prunes nothing under synced dirs"
T=$(new_target); deploy "$T"
if [ -f "$T/.claude/.harness-deployed" ] && [ -d "$T/.claude/skills/xia2" ]; then pass
else fail "manifest missing or a synced entry vanished on first deploy"; fi

t "a harness entry gone from source (in the prior manifest) is pruned on re-sync"
T=$(new_target); deploy "$T"
# simulate a harness skill that existed last deploy but was since deleted from source
echo "skills/_ghost" >> "$T/.claude/.harness-deployed"
mkdir -p "$T/.claude/skills/_ghost"; echo x > "$T/.claude/skills/_ghost/SKILL.md"
deploy "$T"
if [ ! -e "$T/.claude/skills/_ghost" ]; then pass; else fail "orphan _ghost was not pruned"; fi

t "a consumer's own skill (never in the manifest) SURVIVES a re-sync"
T=$(new_target); deploy "$T"
mkdir -p "$T/.claude/skills/consumer-custom"; echo y > "$T/.claude/skills/consumer-custom/SKILL.md"
deploy "$T"
if [ -f "$T/.claude/skills/consumer-custom/SKILL.md" ]; then pass
else fail "consumer's custom skill was destroyed — blind prune hazard"; fi

t "sidecars and backups are never pruned"
T=$(new_target); deploy "$T"
touch "$T/.claude/skills/xia2.harness-incoming"
mkdir -p "$T/.claude/.harness-backup-20260101-000000"; touch "$T/.claude/.harness-backup-20260101-000000/x"
touch "$T/.claude/settings.local.json"
deploy "$T"
if [ -e "$T/.claude/skills/xia2.harness-incoming" ] \
   && [ -e "$T/.claude/.harness-backup-20260101-000000/x" ] \
   && [ -e "$T/.claude/settings.local.json" ]; then pass
else fail "a sidecar/backup/settings.local was pruned"; fi

t "re-sync with no deletions prunes nothing (idempotent)"
T=$(new_target); deploy "$T"
before=$(find "$T/.claude/skills" -maxdepth 1 | sort)
deploy "$T"
after=$(find "$T/.claude/skills" -maxdepth 1 | sort)
if [ "$before" = "$after" ]; then pass; else fail "skills set changed on a no-op re-sync"; fi

t "dry-run reports a would-be prune but writes nothing"
T=$(new_target); deploy "$T"
echo "skills/_ghost2" >> "$T/.claude/.harness-deployed"
mkdir -p "$T/.claude/skills/_ghost2"
out=$(bash "$DEPLOY" --target "$T" --dry-run </dev/null 2>&1)
if printf '%s' "$out" | grep -qF "would prune stale" && [ -d "$T/.claude/skills/_ghost2" ]; then pass
else fail "dry-run did not report, or it deleted: out=$(printf '%s' "$out" | grep -i prune | head -1)"; fi

finish
