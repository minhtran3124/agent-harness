#!/bin/bash
# Contract: deploy-harness.sh and install-harness.sh ship ONE fixed hook set (every hook wired in
# settings.json), with the commit-gate command carrying no --profile argument. The old
# `--profile minimal|standard|strict` flag is accepted but ignored (one-line warning) so existing
# install commands keep working; no .claude/.harness-profile or .claude/harness-manifest.json is
# written, and stale copies from an older deploy are removed. Re-sync also drops harness event
# keys that end up empty instead of leaving `"PostToolUse": []`.
source "$(dirname "$0")/../lib.sh"

DEPLOY="$ROOT/scripts/deploy-harness.sh"
INSTALL="$ROOT/scripts/install-harness.sh"

new_target() { local d; d=$(mktemp -d); _CLEANUP_DIRS+=("$d"); printf '%s' "$d"; }
cmds() { jq -r '[.hooks[][].hooks[].command] | .[]' "$1/.claude/settings.json"; }
gate_cmd() { cmds "$1" | grep '/hooks/commit-gate\.sh' ; }
has_hook() { cmds "$1" | grep -q "/hooks/$2\( \|\$\)"; }
session_matcher() { jq -r --arg c "$2" '[.hooks.SessionStart[]? | select(any(.hooks[]; .command == $c)) | .matcher] | .[]' "$1/.claude/settings.json"; }
listing() { (cd "$1" && find . | LC_ALL=C sort); }

H='$CLAUDE_PROJECT_DIR/.claude/hooks'

# ---------- default deploy ----------
T=$(new_target)
bash "$DEPLOY" --target "$T" >/dev/null 2>&1; rc=$?

t "deploy with no flag exits 0"
if [ "$rc" = 0 ]; then pass; else fail "rc=$rc"; fi

t "deploy registers exactly the four hooks wired in settings.json"
if has_hook "$T" branch-isolation-guard.sh && has_hook "$T" commit-gate.sh && has_hook "$T" session-knowledge.sh \
   && has_hook "$T" model-config.sh && [ "$(cmds "$T" | wc -l | tr -d ' ')" = 4 ]; then pass
else fail "cmds: $(cmds "$T" | tr '\n' '|')"; fi

t "commit-gate command carries no --profile argument"
if [ "$(gate_cmd "$T")" = "$H/commit-gate.sh" ] && ! cmds "$T" | grep -q -- '--profile'; then pass
else fail "got: $(gate_cmd "$T")"; fi

t "model-config.sh is registered under SessionStart with matcher startup|clear"
if [ "$(session_matcher "$T" "$H/model-config.sh")" = "startup|clear" ]; then pass
else fail "matcher: $(session_matcher "$T" "$H/model-config.sh")"; fi

t "no .harness-profile and no harness-manifest.json is written under .claude/"
if [ ! -e "$T/.claude/.harness-profile" ] && [ ! -e "$T/.claude/harness-manifest.json" ]; then pass
else fail "found: $(ls -A "$T/.claude" | tr '\n' ' ')"; fi

t "re-sync never double-registers commit-gate"
bash "$DEPLOY" --target "$T" >/dev/null 2>&1
n=$(cmds "$T" | grep -c '/hooks/commit-gate\.sh')
if [ "$n" = 1 ] && [ "$(gate_cmd "$T")" = "$H/commit-gate.sh" ]; then pass; else fail "commit-gate count=$n"; fi

# ---------- legacy --profile is ignored ----------
for p in minimal standard strict bogus; do
  T=$(new_target)
  err=$(bash "$DEPLOY" --target "$T" --profile "$p" 2>&1 >/dev/null); rc=$?
  t "deploy --profile $p is accepted, ignored, and warns once"
  if [ "$rc" = 0 ] && [ "$(printf '%s\n' "$err" | grep -c 'profile is ignored')" = 1 ] \
     && [ "$(gate_cmd "$T")" = "$H/commit-gate.sh" ] && [ "$(cmds "$T" | wc -l | tr -d ' ')" = 4 ] \
     && [ ! -e "$T/.claude/.harness-profile" ]; then pass
  else fail "rc=$rc err=$err gate=$(gate_cmd "$T" 2>&1)"; fi
done

T=$(new_target)
bash "$DEPLOY" --target "$T" --profile=minimal >/dev/null 2>&1; rc=$?
t "deploy --profile=minimal (equals form) is accepted and ignored"
if [ "$rc" = 0 ] && has_hook "$T" session-knowledge.sh && has_hook "$T" model-config.sh; then pass
else fail "rc=$rc cmds: $(cmds "$T" | tr '\n' '|')"; fi

# ---------- stale files from an older deploy are removed ----------
T=$(new_target)
bash "$DEPLOY" --target "$T" >/dev/null 2>&1
printf 'strict\n' > "$T/.claude/.harness-profile"
printf '{}\n' > "$T/.claude/harness-manifest.json"
bash "$DEPLOY" --target "$T" >/dev/null 2>&1
t "re-sync removes a leftover .harness-profile and harness-manifest.json"
if [ ! -e "$T/.claude/.harness-profile" ] && [ ! -e "$T/.claude/harness-manifest.json" ]; then pass
else fail "still present: $(ls -A "$T/.claude" | tr '\n' ' ')"; fi

t "a recorded old profile no longer changes the hook set"
printf 'minimal\n' > "$T/.claude/.harness-profile"
bash "$DEPLOY" --target "$T" >/dev/null 2>&1
if [ "$(cmds "$T" | wc -l | tr -d ' ')" = 4 ] && [ "$(gate_cmd "$T")" = "$H/commit-gate.sh" ]; then pass
else fail "cmds: $(cmds "$T" | tr '\n' '|')"; fi

# ---------- install-harness ----------
T=$(new_target)
out=$( cd "$T" && bash "$INSTALL" --source "$ROOT" --yes --profile minimal 2>&1 ); rc=$?
t "install --profile minimal succeeds, warns that it is ignored, and ships the fixed set"
if [ "$rc" = 0 ] && printf '%s' "$out" | grep -q 'profile is ignored' \
   && [ "$(gate_cmd "$T")" = "$H/commit-gate.sh" ] && [ "$(cmds "$T" | wc -l | tr -d ' ')" = 4 ]; then pass
else fail "rc=$rc gate=$(gate_cmd "$T" 2>&1)"; fi

t "install without --profile does not warn about profiles"
T=$(new_target)
out=$( cd "$T" && bash "$INSTALL" --source "$ROOT" --yes 2>&1 )
if ! printf '%s' "$out" | grep -qi 'profile'; then pass; else fail "mentions profile: $(printf '%s' "$out" | grep -i profile)"; fi

t "install --help documents --profile as deprecated and ignored"
if bash "$INSTALL" --help | grep -A1 -- '--profile' | grep -qi 'ignored'; then pass
else fail "help text: $(bash "$INSTALL" --help | grep -A2 -- '--profile')"; fi

# ---------- --dry-run writes nothing ----------
T=$(new_target)
before=$(listing "$T")
bash "$DEPLOY" --target "$T" --profile minimal --dry-run >/dev/null 2>&1; rc=$?

t "--dry-run --profile minimal exits 0 and writes nothing"
if [ "$rc" = 0 ] && [ "$(listing "$T")" = "$before" ]; then pass
else fail "rc=$rc target: $(listing "$T" | tr '\n' ' ')"; fi

# ---------- emptied harness events are dropped; foreign hooks survive ----------
T=$(new_target)
mkdir -p "$T/.claude"
cat > "$T/.claude/settings.json" <<'JSON'
{
  "hooks": {
    "PostToolUse": [{"matcher":"Edit|Write","hooks":[{"type":"command","command":"$CLAUDE_PROJECT_DIR/.claude/hooks/ruff-on-edit.sh"}]}],
    "UserPromptSubmit": [{"hooks":[{"type":"command","command":"$CLAUDE_PROJECT_DIR/.claude/hooks/scope-gate.sh"}]}],
    "SessionEnd": [{"hooks":[{"type":"command","command":"$CLAUDE_PROJECT_DIR/.claude/hooks/state-breadcrumb.sh"}]}],
    "Stop": [{"hooks":[{"type":"command","command":"my-stop.sh"}]}]
  }
}
JSON
bash "$DEPLOY" --target "$T" --yes >/dev/null 2>&1

t "re-sync removes emptied PostToolUse / UserPromptSubmit / SessionEnd keys (absent, not [])"
if jq -e '.hooks | (has("PostToolUse") or has("UserPromptSubmit") or has("SessionEnd")) | not' "$T/.claude/settings.json" >/dev/null; then pass
else fail "keys: $(jq -c '.hooks | keys' "$T/.claude/settings.json")"; fi

t "re-sync keeps the foreign Stop hook"
if [ "$(jq -r '.hooks.Stop[0].hooks[0].command' "$T/.claude/settings.json")" = "my-stop.sh" ]; then pass
else fail "Stop: $(jq -c '.hooks.Stop' "$T/.claude/settings.json")"; fi

finish
