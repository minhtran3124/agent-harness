#!/usr/bin/env bash
# PostToolUse(Bash): after `gh pr create`, remind the model to review the PR. Reminds only; never blocks.
command -v jq >/dev/null || exit 0
payload=$(cat)
cmd=$(printf '%s' "$payload" | jq -r '.tool_input.command // empty' 2>/dev/null) || exit 0
printf '%s' "$cmd" | grep -qE '\bgh[[:space:]]+pr[[:space:]]+create\b' || exit 0
pr=$(printf '%s' "$payload" | jq -r '.tool_response | tostring' 2>/dev/null | grep -oE 'github\.com/[^ "]+/pull/[0-9]+' | head -1 | grep -oE '[0-9]+$')
if [ "$(printf '%s' "$payload" | jq -r '.agent_id // empty')" ]; then
  text="PR #${pr:-?} was opened from a subagent. Return the PR number to the main session; subagents do not review."
else
  text="PR #${pr:-?} was opened. Next step: run /code-review on it now, then intent-review, before merge or reporting done. This applies when you finished a stopped or blocked workflow by hand: its review stage did not run."
fi
jq -n --arg t "$text" '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$t}}'
