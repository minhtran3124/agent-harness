---
ticket: 643
stage: design
status: accepted
confidence: medium
decided_by: owner
date: 2026-11-16
---

# 0034. Send tool names and token counts to the board

## Context

The board README said the board "never sends prompts, tool calls or file contents". Issue #643 restyles the Workflow boxes as crew-style cards. A card shows how much context an agent has used and which tools it uses. Both come from the agent transcript (`agent-<id>.jsonl`), which the board already reads for time, model and effort.

## Options

- Keep the old rule: no tokens, no tools. The cards show `tokens n/a` and no icons.
- Send the token count and the tool names. Never send tool input or output, prompts or answers.
- Send the latest assistant text as the live activity line.

## Decision

The board sends two new fields on the `agent_facts` event: `tokens` (a number), and `tools` and `tool` (tool names that match `^[A-Za-z0-9_.:-]{1,60}$`; at most 40 names, in first-use order; `tool` is the latest). The live activity line shows `Using <tool>` and never assistant text. The board still sends no prompt, no answer, no tool input and no tool output.

## Why

A tool name tells the owner what an agent is doing and carries no file content. The assistant text and the tool input can hold file paths, commands and secrets, so they stay out. A name can still show what an agent does in a project, so the README names the fields.

## Consequences

Enables: live activity, tool icons and a token bar on every card. Costs: the Privacy rule of the board changes for tool names. The token count has no limit table yet (the owner gives the values in `flow.json` `models`), so cards show `tokens n/a` until then. The transcript layout is not a public contract: if `usage` or `tool_use` blocks vanish, the cards fall back to the label subject and `tokens n/a`. Not verified against a real transcript in this change (the fixtures follow the Claude Code layout from memory).

## How to reverse

Remove `tokens`, `tools` and `tool` from `agentFacts` in `board.js`. The cards fall back by themselves.
