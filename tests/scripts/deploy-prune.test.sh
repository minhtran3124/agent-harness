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

t "Claude agents are rendered while source-time binding JSON stays undeployed"
T=$(new_target); deploy "$T"
if grep -q '^model: claude-sonnet-5-5$' "$T/.claude/agents/intent-reviewer.md" \
   && grep -q '^tools: Glob, Grep, Read, Bash$' "$T/.claude/agents/intent-reviewer.md" \
   && [ ! -e "$T/.claude/agents/agent-contracts.json" ] \
   && [ ! -e "$T/.claude/agents/runtime-bindings.json" ]; then pass
else fail "rendered intent-reviewer or source-time binding boundary is wrong"; fi

t "a consumer's custom agent survives rendered-agent re-sync"
T=$(new_target); deploy "$T"
printf '%s\n' custom > "$T/.claude/agents/consumer-custom.md"
deploy "$T"
if [ "$(cat "$T/.claude/agents/consumer-custom.md")" = custom ]; then pass
else fail "consumer custom agent was overwritten or pruned"; fi

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

t "v4 leftovers (runtime/, removed scripts and templates) are pruned; a consumer's own .claude/runtime file survives"
T=$(new_target); deploy "$T"
# simulate a consumer last synced by v4: its manifest lists files source no longer ships
mkdir -p "$T/.claude/runtime" "$T/.claude/scripts"
echo x > "$T/.claude/runtime/run_state.py"; echo x > "$T/.claude/runtime/resume_decision.py"
echo x > "$T/.claude/scripts/verify_summary.py"; echo x > "$T/.claude/templates/SUMMARY.template.md"
printf '%s\n' runtime/run_state.py runtime/resume_decision.py scripts/verify_summary.py templates/SUMMARY.template.md >> "$T/.claude/.harness-deployed"
echo mine > "$T/.claude/runtime/consumer-own.py"
deploy "$T"
if [ ! -e "$T/.claude/runtime/run_state.py" ] && [ ! -e "$T/.claude/runtime/resume_decision.py" ] \
   && [ ! -e "$T/.claude/scripts/verify_summary.py" ] && [ ! -e "$T/.claude/templates/SUMMARY.template.md" ] \
   && [ "$(cat "$T/.claude/runtime/consumer-own.py")" = mine ]; then pass
else fail "stale v4 files not pruned, or the consumer's own runtime file was lost: $(ls "$T/.claude/runtime" 2>&1 | tr '\n' ' ')"; fi

t "an emptied legacy .claude/runtime/ directory is removed after the prune"
T=$(new_target); deploy "$T"
mkdir -p "$T/.claude/runtime"; echo x > "$T/.claude/runtime/run_state.py"
echo runtime/run_state.py >> "$T/.claude/.harness-deployed"
deploy "$T"
if [ ! -e "$T/.claude/runtime" ]; then pass; else fail "empty runtime/ dir left behind"; fi

t "a fresh deploy never creates .claude/runtime/"
T=$(new_target); deploy "$T"
if [ ! -e "$T/.claude/runtime" ]; then pass; else fail "runtime/ deployed"; fi

t "dry-run reports a would-be prune but writes nothing"
T=$(new_target); deploy "$T"
echo "skills/_ghost2" >> "$T/.claude/.harness-deployed"
mkdir -p "$T/.claude/skills/_ghost2"
out=$(bash "$DEPLOY" --target "$T" --dry-run </dev/null 2>&1)
if printf '%s' "$out" | grep -qF "would prune stale" && [ -d "$T/.claude/skills/_ghost2" ]; then pass
else fail "dry-run did not report, or it deleted: out=$(printf '%s' "$out" | grep -i prune | head -1)"; fi

t "a re-sync prunes the nine removed v4 rules, keeps rules/behavior.md and a consumer's own rule"
T=$(new_target); deploy "$T"
OLD_RULES="architecture auto-correct-scope guidelines orchestration plan-format research-depth review-policy terminology wave-parallelism"
for r in $OLD_RULES; do
  printf 'old %s\n' "$r" > "$T/.claude/rules/$r.md"
  echo "rules/$r.md" >> "$T/.claude/.harness-deployed"
done
echo mine > "$T/.claude/rules/consumer-own.md"
deploy "$T"
left=""
for r in $OLD_RULES; do [ -e "$T/.claude/rules/$r.md" ] && left="$left $r.md"; done
if [ -z "$left" ] && [ -f "$T/.claude/rules/behavior.md" ] \
   && [ "$(cat "$T/.claude/rules/consumer-own.md")" = mine ] \
   && [ "$(ls "$T/.claude/rules" | grep -v '^consumer-own\.md$' | tr '\n' ' ')" = "behavior.md " ]; then pass
else fail "removed rules left behind:$left; rules/ now: $(ls "$T/.claude/rules" | tr '\n' ' ')"; fi

t "a pruned architecture.md / guidelines.md is backed up first (they were consumer-owned)"
T=$(new_target); deploy "$T"
printf 'my stack notes\n' > "$T/.claude/rules/architecture.md"
printf 'my style notes\n' > "$T/.claude/rules/guidelines.md"
printf '%s\n' rules/architecture.md rules/guidelines.md >> "$T/.claude/.harness-deployed"
deploy "$T"
if [ ! -e "$T/.claude/rules/architecture.md" ] && [ ! -e "$T/.claude/rules/guidelines.md" ] \
   && [ "$(cat "$T/.claude/.harness-backup-pruned/rules/architecture.md")" = "my stack notes" ] \
   && [ "$(cat "$T/.claude/.harness-backup-pruned/rules/guidelines.md")" = "my style notes" ]; then pass
else fail "backup missing: $(ls -R "$T/.claude/.harness-backup-pruned" 2>&1 | tr '\n' ' ')"; fi

finish
