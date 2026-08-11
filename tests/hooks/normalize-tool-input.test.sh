#!/usr/bin/env bash
# Contract tests for the runtime-neutral hook payload normalizer.
source "$(dirname "$0")/../lib.sh"

NORMALIZER="$ROOT/hooks/lib/normalize-tool-input.py"
FIXTURES="$ROOT/tests/fixtures/hook-input"
REPO=$(mktemp -d); _CLEANUP_DIRS+=("$REPO")
mkdir -p "$REPO/src" "$REPO/specs/demo"

normalize() {
  OUT=$(python3 "$NORMALIZER" --root "$REPO" < "$FIXTURES/$1" 2>&1); RC=$?
}

assert_json() {
  local expression="$1"
  if [ "$RC" -eq 0 ] && printf '%s' "$OUT" | jq -e "$expression" >/dev/null 2>&1; then
    pass
  else
    fail "rc=$RC jq=[$expression] out=[$OUT]"
  fi
}

t "Claude shell becomes a known shell command"
normalize claude-shell.json
assert_json '.runtime == "claude" and .tool_class == "shell" and .status == "known" and .command == "git status"'

t "Claude Write becomes one repository-relative path"
normalize claude-write.json
assert_json '.runtime == "claude" and .tool_class == "edit" and .status == "known" and .paths == ["src/example.py"]'

t "Codex shell uses the same canonical shell contract"
normalize codex-shell.json
assert_json '.runtime == "codex" and .tool_class == "shell" and .status == "known" and (.command | startswith("git commit"))'

t "documented unified exec hook shape normalizes as Bash"
normalize codex-unified-exec.json
assert_json '.runtime == "codex" and .tool_class == "shell" and .status == "known" and .outcome.exit_code == 0'

t "single-file apply_patch extracts its update path"
normalize codex-apply-patch-single.json
assert_json '.status == "known" and .paths == ["src/example.py"]'

t "multi-file apply_patch preserves all paths including spaces"
normalize codex-apply-patch-multi.json
assert_json '.status == "known" and .paths == ["specs/demo/PLAN.md","src/new file.py","src/old.py"]'

t "move/delete patch retains source, destination, and deleted path"
normalize codex-apply-patch-move-delete.json
assert_json '.status == "known" and .paths == ["src/current.py","src/legacy.py","src/unused.py"]'

t "Claude UserPromptSubmit uses the canonical prompt field"
normalize claude-user-prompt.json
assert_json '.runtime == "claude" and .tool_class == "prompt" and .status == "known"'

t "Codex UserPromptSubmit uses the same canonical prompt field"
normalize codex-user-prompt.json
assert_json '.runtime == "codex" and .tool_class == "prompt" and .status == "known"'

t "malformed JSON stays machine-readable and explicitly unknown"
normalize malformed.json
assert_json '.status == "unknown" and (.diagnostics[0] | startswith("malformed-json:"))'

t "one unsafe sibling makes a patch partial without hiding valid paths"
OUT=$(printf '%s' '{"turn_id":"t","hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: specs/demo/PLAN.md\n*** Add File: ../escape.py\n*** End Patch"}}' | python3 "$NORMALIZER" --root "$REPO"); RC=$?
assert_json '.status == "partial" and .paths == ["specs/demo/PLAN.md"] and (.diagnostics | index("unsafe-path:outside-root"))'

t "NUL path is rejected as partial while a safe sibling survives"
OUT=$(printf '%s' '{"turn_id":"t","hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: src/good.py\n*** Add File: bad\u0000.py\n*** End Patch"}}' | python3 "$NORMALIZER" --root "$REPO"); RC=$?
assert_json '.status == "partial" and .paths == ["src/good.py"] and (.diagnostics | index("unsafe-path:nul-path"))'

t "unrecognized patch control line is fail-visible"
OUT=$(printf '%s' '{"turn_id":"t","hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update Binary File: src/x.bin\n*** End Patch"}}' | python3 "$NORMALIZER" --root "$REPO"); RC=$?
assert_json '.status == "unknown" and (.diagnostics | index("patch-unparsed-control"))'

t "tool_name-less patch with a leading newline is an edit, never a shell command"
# Regression (Phase-4 review F1): the shell branch used to claim any tool_name-less
# command not starting at offset 0 with the patch marker, yielding shell/known with an
# empty path set — which branch-isolation read as an allowable no-op on a shared branch.
OUT=$(printf '%s' '{"turn_id":"t","hook_event_name":"PreToolUse","tool_input":{"command":"\n*** Begin Patch\n*** Update File: src/app.py\n*** End Patch"}}' | python3 "$NORMALIZER" --root "$REPO"); RC=$?
assert_json '.tool_class == "edit" and .status != "known" and .paths == ["src/app.py"]'

t "tool_name-less plain command still classifies as shell"
OUT=$(printf '%s' '{"turn_id":"t","hook_event_name":"PreToolUse","tool_input":{"command":"ls -la"}}' | python3 "$NORMALIZER" --root "$REPO"); RC=$?
assert_json '.tool_class == "shell" and .status == "known" and .command == "ls -la"'

t "output schema is stable and contains every canonical field"
normalize codex-shell.json
assert_json 'keys == ["command","diagnostics","event","outcome","paths","prompt","runtime","schema_version","status","tool_class"]'

t "Windows absolute path is rejected on every host"
OUT=$(printf '%s' '{"turn_id":"t","hook_event_name":"PreToolUse","tool_name":"apply_patch","tool_input":{"command":"*** Begin Patch\n*** Update File: C:\\\\private\\\\x.py\n*** End Patch"}}' | python3 "$NORMALIZER" --root "$REPO"); RC=$?
assert_json '.status == "unknown" and (.diagnostics | index("unsafe-path:outside-root"))'

t "large tool response is represented by bounded outcome metadata"
OUT=$(printf '%s' '{"turn_id":"t","hook_event_name":"PostToolUse","tool_name":"Bash","tool_input":{"command":"true"},"tool_response":{"exit_code":0,"output":"secret-or-very-large-output"}}' | python3 "$NORMALIZER" --root "$REPO"); RC=$?
assert_json '.outcome == {"exit_code":0,"present":true} and (tostring | contains("secret-or-very-large-output") | not)'

t "every declared Phase 4 hook consumer uses the shared normalizer"
MISSING_CONSUMERS=""
for HOOK in \
  blast-radius-check.sh \
  branch-isolation-guard.sh \
  pre-bash-dispatch.sh \
  render-plan-on-write.sh \
  ruff-on-edit.sh \
  scope-gate.sh; do
  if ! grep -q 'normalize-tool-input.py' "$ROOT/hooks/$HOOK"; then
    MISSING_CONSUMERS="${MISSING_CONSUMERS}${MISSING_CONSUMERS:+,}$HOOK"
  fi
done
if [ -z "$MISSING_CONSUMERS" ]; then
  pass
else
  fail "missing normalizer consumers: $MISSING_CONSUMERS"
fi

finish
