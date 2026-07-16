#!/bin/bash
# Regression: deploy-harness.sh must MERGE into an existing .claude/settings.json, never
# replace it. A consuming project may carry its own top-level keys (permissions, env,
# statusLine, enabledPlugins) and its own hooks — re-sync must preserve all of them while
# keeping the harness hook set deduplicated (idempotent, no double-registration).
source "$(dirname "$0")/../lib.sh"

DEPLOY="$ROOT/scripts/deploy-harness.sh"

T=$(mktemp -d); _CLEANUP_DIRS+=("$T")
S="$T/.claude/settings.json"

# First install.
bash "$DEPLOY" --target "$T" >/dev/null 2>&1

t "first install produces valid .claude/settings.json"
if jq -e . "$S" >/dev/null 2>&1; then pass; else fail "not valid JSON / missing"; fi

# Simulate a consuming project: add foreign top-level keys + a foreign hook under an event the
# harness also uses (PostToolUse) + a foreign event the harness does not use (Stop).
jq '. + {permissions:{allow:["Bash(npm *)"]}, statusLine:{type:"command",command:"my-line"}}
    | .hooks.PostToolUse += [{"matcher":"Write","hooks":[{"type":"command","command":"my-own-hook.sh"}]}]
    | .hooks.Stop = [{"hooks":[{"type":"command","command":"my-stop.sh"}]}]' \
  "$S" > "$S.tmp" && mv "$S.tmp" "$S"

# Re-sync twice — must be idempotent.
bash "$DEPLOY" --target "$T" >/dev/null 2>&1
bash "$DEPLOY" --target "$T" >/dev/null 2>&1

t "re-sync keeps foreign top-level keys (permissions, statusLine)"
if [ "$(jq -r '.permissions.allow[0]' "$S")" = "Bash(npm *)" ] \
   && [ "$(jq -r '.statusLine.command' "$S")" = "my-line" ]; then pass
else fail "foreign top-level keys lost: $(jq -c 'keys' "$S")"; fi

t "re-sync keeps a foreign hook under a harness-shared event (PostToolUse)"
n=$(jq '[.hooks[][].hooks[] | select((.command//"")=="my-own-hook.sh")] | length' "$S")
if [ "$n" = "1" ]; then pass; else fail "my-own-hook.sh count=$n, want 1"; fi

t "re-sync keeps a foreign event the harness does not touch (Stop)"
n=$(jq '[.hooks[][].hooks[] | select((.command//"")=="my-stop.sh")] | length' "$S")
if [ "$n" = "1" ]; then pass; else fail "my-stop.sh count=$n, want 1"; fi

t "re-sync does not double-register a harness hook (idempotent)"
n=$(jq '[.hooks[][].hooks[] | select((.command//"")|test("ruff-on-edit"))] | length' "$S")
if [ "$n" = "1" ]; then pass; else fail "ruff-on-edit count=$n after 2 re-syncs, want 1"; fi

t "harness hook commands are derived to \$CLAUDE_PROJECT_DIR/.claude/ on re-sync"
if jq -e '[.hooks[][].hooks[].command] | any(startswith("$CLAUDE_PROJECT_DIR/.claude/hooks/"))' "$S" >/dev/null; then pass
else fail "no derived harness command path found"; fi

# Invalid existing settings.json: cannot merge — must back up (not silently overwrite),
# then write a fresh valid file.
T2=$(mktemp -d); _CLEANUP_DIRS+=("$T2")
mkdir -p "$T2/.claude"
printf '{ this is NOT valid json,,, ' > "$T2/.claude/settings.json"
bash "$DEPLOY" --target "$T2" >/dev/null 2>&1

t "invalid existing settings.json is backed up, not silently overwritten"
n=$(ls "$T2/.claude/"settings.json.invalid-bak-* 2>/dev/null | wc -l | tr -d ' ')
if [ "$n" -ge 1 ]; then pass; else fail "no settings.json.invalid-bak-* backup created"; fi

t "backup preserves the original invalid content"
bak=$(ls "$T2/.claude/"settings.json.invalid-bak-* 2>/dev/null | head -1)
if grep -q 'NOT valid json' "$bak" 2>/dev/null; then pass; else fail "backup missing original content"; fi

t "a fresh valid harness settings.json is written after invalid backup"
if jq -e '[.hooks[][].hooks[].command] | any(startswith("$CLAUDE_PROJECT_DIR/.claude/hooks/"))' "$T2/.claude/settings.json" >/dev/null 2>&1; then pass
else fail "replacement settings.json is not valid / missing harness hooks"; fi

finish
