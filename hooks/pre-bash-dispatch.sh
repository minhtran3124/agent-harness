#!/bin/bash
# PreToolUse Bash dispatcher: fan out to the four git-command sub-hooks in settings order.
#
# The slimmed hook surface registers ONE PreToolUse Bash hook; this dispatcher runs the
# git-command hooks that were previously registered as four separate entries. It preserves
# every existing block/warn decision — the sub-hooks are invoked unchanged.
#
# CONTRACT (invariant #1): each sub-hook's stdout is relayed UNCONDITIONALLY, regardless of
# the sub-hook's exit code. check-untracked-py.sh denies by printing a
# permissionDecision:"deny" JSON to stdout and then EXITING 0 — a dispatcher that only
# forwarded on exit 2 would silently drop that hard block. Child stdout flows straight to
# this hook's stdout and child stderr straight to its stderr (streams are never merged). A
# sub-hook exit 2 is an independent early-stop: its stdout is already relayed, then the
# dispatcher propagates exit 2.
#
# On non-commit/push Bash commands (the common case) this fast-paths exit 0 without spawning
# any sub-hook, preserving the raw payload relay expected by those consumers.

INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"

# Fast path: `tool_name == "Bash"` with a non-empty string command is the one shape the
# normalizer can only ever classify as shell/known, so resolving it here is equivalent —
# and it keeps the common case at one jq with no Python process. This hook runs on EVERY
# Bash tool call; spawning an interpreter to re-derive a value already unambiguous in the
# raw payload cost ~5x the whole hook's budget. Anything else goes to the normalizer.
CMD=$(printf '%s' "$INPUT" | jq -r '
  if (.tool_name == "Bash") and (.tool_input.command | type == "string") and (.tool_input.command != "")
  then .tool_input.command else empty end' 2>/dev/null)

if [ -z "$CMD" ]; then
  NORMALIZER="$SCRIPT_DIR/lib/normalize-tool-input.py"
  if command -v python3 >/dev/null 2>&1 && [ -f "$NORMALIZER" ]; then
    NORMALIZED=$(printf '%s' "$INPUT" | python3 "$NORMALIZER" --root "$ROOT" 2>/dev/null)
  else
    NORMALIZED='{"status":"unknown","tool_class":"unknown","command":null,"diagnostics":["normalizer-unavailable"]}'
  fi
  # One jq for the gate decision (all three values are single-line by construction:
  # status/tool_class are enum tokens, diagnostics are fixed slugs joined with ", ").
  { read -r STATUS; read -r TOOL_CLASS; read -r DIAG; } <<EOF
$(printf '%s' "$NORMALIZED" | jq -r '
    (.status // "unknown"),
    (.tool_class // "unknown"),
    ((.diagnostics // []) | join(", "))' 2>/dev/null)
EOF
  if [ "${STATUS:-unknown}" != "known" ] || [ "${TOOL_CLASS:-unknown}" != "shell" ]; then
    echo "[PRE-BASH DISPATCH] could not safely classify Bash payload (${DIAG:-unparsed payload}) — redeploy/update the harness normalizer (blocking to fail safe)." >&2
    exit 2
  fi
  # Command is extracted separately: it may be multi-line, which a line-oriented read
  # would silently truncate — and a truncated command is what the git matcher tokenizes.
  CMD=$(printf '%s' "$NORMALIZED" | jq -r '.command // ""' 2>/dev/null)
fi

# Only fan out for git commit/push (tokenizing matcher — resists cd/&&/-C/-c bypass).
source "$SCRIPT_DIR/lib/git-command.sh" 2>/dev/null
# Fail closed: if the matcher lib is missing, block rather than skip every gate below.
command -v hook_cmd_is_git_commit_or_push >/dev/null 2>&1 || {
  echo "[PRE-BASH DISPATCH] git-command matcher lib missing — redeploy harness (blocking to fail safe)." >&2
  exit 2
}
hook_cmd_is_git_commit_or_push "$CMD" || exit 0

# Sub-hooks in the original settings.json PreToolUse Bash order. Each self-filters commit vs
# push internally, so on `git push` only check-untracked-py.sh acts.
for hook in check-untracked-py.sh commit-quality-gate.sh risk-corroboration.sh branch-guard.sh; do
  path="$SCRIPT_DIR/$hook"
  # Fail closed: a missing sub-hook must block, not silently skip a gate.
  if [ ! -f "$path" ]; then
    echo "[PRE-BASH DISPATCH] sub-hook missing: hooks/$hook — redeploy harness (blocking to fail safe)." >&2
    exit 2
  fi
  # Relay child stdout unconditionally (fd1→fd1, fd2→fd2; not merged) so untracked-py's
  # stdout-JSON deny reaches Claude even though that hook exits 0.
  printf '%s' "$INPUT" | bash "$path"
  rc=$?
  # An exit-2 block is an independent early-stop: stdout is already relayed, now propagate.
  [ "$rc" -eq 2 ] && exit 2
done

exit 0
