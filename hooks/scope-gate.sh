#!/bin/bash
# UserPromptSubmit hook: warn when an implementation-intent prompt has no plan referenced.
# Non-blocking — injects additionalContext, never denies.

INPUT=$(cat)
PROMPT=$(printf '%s' "$INPUT" | jq -r '.prompt // ""')
WORD_COUNT=$(printf '%s' "$PROMPT" | wc -w)

IS_IMPL=0
printf '%s' "$PROMPT" | grep -qiE '\b(add|implement|refactor|build|create|fix|change|improve|migrat|integrat)\b' && IS_IMPL=1

HAS_PLAN=0
printf '%s' "$PROMPT" | grep -qiE 'specs/|\bplan\b' && HAS_PLAN=1

if [ "$WORD_COUNT" -gt 6 ] && [ "$IS_IMPL" -eq 1 ] && [ "$HAS_PLAN" -eq 0 ]; then
  # Dedup: don't repeat the nudge once intake has already run / is in flight for the
  # current task (hooks/lib/lane.sh) — every UserPromptSubmit re-fires this hook fresh,
  # so without this a multi-turn task nags on every qualifying follow-up message even
  # after the Lane question is already answered. A missing lib falls through to the
  # nudge (today's behavior) — safe default since the nudge itself never blocks.
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
  REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
  [ -z "$REPO_DIR" ] && REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
  source "$SCRIPT_DIR/lib/lane.sh" 2>/dev/null
  if command -v hook_lib_intake_in_progress >/dev/null 2>&1 && hook_lib_intake_in_progress "$REPO_DIR"; then
    exit 0
  fi

  jq -cn '{
    hookSpecificOutput: {
      hookEventName: "UserPromptSubmit",
      additionalContext: "Implementation-intent request with no plan referenced. Run /feature-intake to set the lane. Tiny lane → proceed with a direct edit (no confirmation needed). Normal/high-risk → produce a plan first. Pause for the human only if the direction is ambiguous, confidence is low, or a hard gate fires (auth/authz/data-loss/migration/audit/external-provider/public-contract/high-blast file)."
    }
  }'
fi
