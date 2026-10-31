---
ticket: 545
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-31
---

# 0128. No UserPromptSubmit token fallback: ask is honored under bypassPermissions

## Context

Ticket says add a token fallback only if ask is ignored under bypassPermissions (the owner's shell uses --dangerously-skip-permissions).

## Options

- Build the token fallback
- Rely on ask only

## Decision

Rely on ask only; no token hook.

## Why

Live probe with a throwaway PreToolUse hook printing ask, run as `claude -p --permission-mode default|auto|bypassPermissions`: in all three modes the Bash call was blocked (error 'probe ask'), never run. The hook payload carried permission_mode equal to the mode in each case. So ask is not turned into an allow in any mode. Limit: headless -p has no one to answer, so a live Yes under interactive bypassPermissions was not observed; only that it is not silently allowed. A token file could be forged by a Bash-capable agent, so it would only guard mistakes.

## Consequences

The hook cannot detect -p itself; it relies on Claude Code denying an unanswered ask (observed). The hook denies by itself for dontAsk, plan, missing or unknown permission_mode and for a payload with agent_id.

## How to reverse

Add a UserPromptSubmit hook that writes a single-use token bound to one PR and session with a short expiry, and have merge-guard.sh consume it.
