#!/bin/bash
# Contract: deploy-harness.sh and install-harness.sh honor `--profile minimal|standard|strict`.
# The profile filters the derived hook set (harness-manifest.json hook_profiles), appends
# ` --profile <p>` to the commit-gate command only, persists to .claude/.harness-profile, is reused
# on a flagless re-sync, and an unknown value is rejected before any write. Re-sync also drops
# harness event keys that end up empty instead of leaving `"PostToolUse": []`.
source "$(dirname "$0")/../lib.sh"

DEPLOY="$ROOT/scripts/deploy-harness.sh"
INSTALL="$ROOT/scripts/install-harness.sh"

new_target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); printf '%s' "$d"; }
cmds() { jq -r '[.hooks[][].hooks[].command] | .[]' "$1/.claude/settings.json"; }
gate_cmd() { cmds "$1" | grep '/hooks/commit-gate\.sh' ; }
has_hook() { cmds "$1" | grep -q "/hooks/$2\( \|\$\)"; }
profile_flag_count() { cmds "$1" | grep -c -- '--profile' ; }
listing() { (cd "$1" && find . | LC_ALL=C sort); }

H='$CLAUDE_PROJECT_DIR/.claude/hooks'

# ---------- minimal ----------
T=$(new_target)
bash "$DEPLOY" --target "$T" --profile minimal >/dev/null 2>&1; rc=$?

t "--profile minimal deploys (exit 0)"
if [ "$rc" = 0 ]; then pass; else fail "rc=$rc"; fi

t "--profile minimal registers exactly branch-isolation-guard + commit-gate --profile minimal"
got=$(cmds "$T" | LC_ALL=C sort | tr '\n' '|')
want=$(printf '%s\n' "$H/branch-isolation-guard.sh" "$H/commit-gate.sh --profile minimal" | LC_ALL=C sort | tr '\n' '|')
if [ "$got" = "$want" ]; then pass; else fail "got: $got"; fi

t "--profile minimal drops the SessionStart key entirely"
if jq -e '.hooks | has("SessionStart") | not' "$T/.claude/settings.json" >/dev/null; then pass
else fail "keys: $(jq -c '.hooks | keys' "$T/.claude/settings.json")"; fi

t ".claude/.harness-profile records minimal"
if [ "$(cat "$T/.claude/.harness-profile" 2>/dev/null)" = "minimal" ]; then pass
else fail "got: $(cat "$T/.claude/.harness-profile" 2>&1)"; fi

t "flagless re-sync reuses the recorded profile (minimal stays minimal)"
bash "$DEPLOY" --target "$T" >/dev/null 2>&1
if [ "$(gate_cmd "$T")" = "$H/commit-gate.sh --profile minimal" ] && ! has_hook "$T" session-knowledge.sh \
   && [ "$(cat "$T/.claude/.harness-profile")" = "minimal" ]; then pass
else fail "gate=$(gate_cmd "$T") profile=$(cat "$T/.claude/.harness-profile")"; fi

t ".harness-profile survives prune_orphans across re-syncs"
bash "$DEPLOY" --target "$T" >/dev/null 2>&1
if [ -f "$T/.claude/.harness-profile" ] && ! grep -q 'harness-profile' "$T/.claude/.harness-deployed"; then pass
else fail "profile file missing or recorded in .harness-deployed"; fi

t "an explicit --profile on re-sync overrides and rewrites the file"
bash "$DEPLOY" --target "$T" --profile=strict >/dev/null 2>&1
if [ "$(cat "$T/.claude/.harness-profile")" = "strict" ] \
   && [ "$(gate_cmd "$T")" = "$H/commit-gate.sh --profile strict" ] && has_hook "$T" session-knowledge.sh; then pass
else fail "gate=$(gate_cmd "$T") profile=$(cat "$T/.claude/.harness-profile")"; fi

t "re-sync never double-registers commit-gate across a profile change"
n=$(cmds "$T" | grep -c '/hooks/commit-gate\.sh')
if [ "$n" = 1 ]; then pass; else fail "commit-gate count=$n"; fi

# ---------- default (standard) ----------
T=$(new_target)
bash "$DEPLOY" --target "$T" >/dev/null 2>&1

t "default (fresh, no flag) registers all three standard hooks"
if has_hook "$T" branch-isolation-guard.sh && has_hook "$T" commit-gate.sh && has_hook "$T" session-knowledge.sh \
   && [ "$(cmds "$T" | wc -l | tr -d ' ')" = 3 ]; then pass
else fail "cmds: $(cmds "$T" | tr '\n' '|')"; fi

t "default commit-gate command ends with exactly ' --profile standard'"
if [ "$(gate_cmd "$T")" = "$H/commit-gate.sh --profile standard" ]; then pass
else fail "got: $(gate_cmd "$T")"; fi

t "no hook other than commit-gate carries --profile"
if [ "$(profile_flag_count "$T")" = 1 ]; then pass
else fail "commands with --profile: $(profile_flag_count "$T")"; fi

t "default records standard in .harness-profile"
if [ "$(cat "$T/.claude/.harness-profile" 2>/dev/null)" = "standard" ]; then pass; else fail "missing/wrong"; fi

# ---------- strict ----------
T=$(new_target)
bash "$DEPLOY" --target "$T" --profile strict >/dev/null 2>&1

t "--profile strict: commit-gate carries exactly ' --profile strict', and only it"
if [ "$(gate_cmd "$T")" = "$H/commit-gate.sh --profile strict" ] && [ "$(profile_flag_count "$T")" = 1 ]; then pass
else fail "gate=$(gate_cmd "$T")"; fi

# ---------- unknown profile: rejected before any write ----------
T=$(new_target)
before=$(listing "$T")
bash "$DEPLOY" --target "$T" --profile bogus >/dev/null 2>&1; rc=$?

t "deploy --profile bogus exits non-zero"
if [ "$rc" != 0 ]; then pass; else fail "rc=0"; fi

t "deploy --profile bogus writes nothing into the target"
if [ "$(listing "$T")" = "$before" ]; then pass; else fail "target changed: $(listing "$T" | tr '\n' ' ')"; fi

T=$(new_target)
before=$(listing "$T")
( cd "$T" && bash "$INSTALL" --source "$ROOT" --yes --profile bogus ) >/dev/null 2>&1; rc=$?

t "install --profile bogus exits non-zero"
if [ "$rc" != 0 ]; then pass; else fail "rc=0"; fi

t "install --profile bogus writes nothing (no .mcp.json, no .claude/)"
if [ "$(listing "$T")" = "$before" ] && [ ! -e "$T/.mcp.json" ]; then pass
else fail "target changed: $(listing "$T" | tr '\n' ' ')"; fi

t "install --profile minimal forwards the profile to deploy"
T=$(new_target)
( cd "$T" && bash "$INSTALL" --source "$ROOT" --yes --profile minimal ) >/dev/null 2>&1
if [ "$(cat "$T/.claude/.harness-profile" 2>/dev/null)" = "minimal" ] \
   && [ "$(gate_cmd "$T")" = "$H/commit-gate.sh --profile minimal" ]; then pass
else fail "profile=$(cat "$T/.claude/.harness-profile" 2>&1) gate=$(gate_cmd "$T" 2>&1)"; fi

# ---------- --dry-run with --profile writes nothing ----------
T=$(new_target)
before=$(listing "$T")
bash "$DEPLOY" --target "$T" --profile minimal --dry-run >/dev/null 2>&1; rc=$?

t "--dry-run --profile minimal exits 0 and writes nothing"
if [ "$rc" = 0 ] && [ "$(listing "$T")" = "$before" ]; then pass
else fail "rc=$rc target: $(listing "$T" | tr '\n' ' ')"; fi

# ---------- emptied harness events are dropped; foreign hooks survive ----------
T=$(new_target)
mkdir -p "$T/.claude"
cat > "$T/.claude/settings.json" <<'EOF'
{
  "hooks": {
    "PostToolUse": [{"matcher":"Edit|Write","hooks":[{"type":"command","command":"$CLAUDE_PROJECT_DIR/.claude/hooks/ruff-on-edit.sh"}]}],
    "UserPromptSubmit": [{"hooks":[{"type":"command","command":"$CLAUDE_PROJECT_DIR/.claude/hooks/scope-gate.sh"}]}],
    "SessionEnd": [{"hooks":[{"type":"command","command":"$CLAUDE_PROJECT_DIR/.claude/hooks/state-breadcrumb.sh"}]}],
    "Stop": [{"hooks":[{"type":"command","command":"my-stop.sh"}]}]
  }
}
EOF
bash "$DEPLOY" --target "$T" --yes >/dev/null 2>&1

t "re-sync removes emptied PostToolUse / UserPromptSubmit / SessionEnd keys (absent, not [])"
if jq -e '.hooks | (has("PostToolUse") or has("UserPromptSubmit") or has("SessionEnd")) | not' "$T/.claude/settings.json" >/dev/null; then pass
else fail "keys: $(jq -c '.hooks | keys' "$T/.claude/settings.json")"; fi

t "re-sync keeps the foreign Stop hook"
if [ "$(jq -r '.hooks.Stop[0].hooks[0].command' "$T/.claude/settings.json")" = "my-stop.sh" ]; then pass
else fail "Stop: $(jq -c '.hooks.Stop' "$T/.claude/settings.json")"; fi

t "--profile -eminimal (option-shaped value) is rejected, not parsed as a grep flag"
T2=$(mktemp -d); _CLEANUP_DIRS+=("$T2")
if bash "$DEPLOY" --target "$T2" --yes --profile -eminimal >/dev/null 2>&1; then fail "deploy accepted -eminimal"
elif [ -e "$T2/.claude" ]; then fail "deploy wrote .claude before rejecting"
else pass; fi

t "install's accepted profile names equal the manifest hook_profiles keys"
want=$(jq -r '.hook_profiles | keys[] | select(. != "default")' "$ROOT/harness-manifest.json" | sort | tr '\n' ' ')
got=$(grep -oE '^  ""\|[a-z|]+\) ;;' "$INSTALL" | sed -E 's/^  ""\|//; s/\) ;;$//' | tr '|' '\n' | sort | tr '\n' ' ')
if [ -n "$got" ] && [ "$got" = "$want" ]; then pass
else fail "install accepts [$got], manifest has [$want]"; fi

finish
