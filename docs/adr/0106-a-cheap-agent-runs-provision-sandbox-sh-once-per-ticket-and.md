---
ticket: 477
stage: design
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: design)
date: 2026-10-29
---

# 0106. A cheap agent runs provision-sandbox.sh once per ticket and returns its JSON line

## Context

A Workflow script has no shell. ADR 0002 decision 1 makes each stage agent run git worktree add through newWt. Ticket #477 wants the script to provision one sandbox per ticket.

## Options

- Dedicated stageProvision agent (cheap model, SANDBOX_SCHEMA) before implement
- Fold provisioning into the implement agent prompt
- Provision from a hook

## Decision

Add stageProvision(t) on the cheap model with SANDBOX_SCHEMA {status, dir, branch, port, db, error}. runTicket runs it after the plan and before implement, and throws Blocked with the script's stderr message when it fails. Implement, verify (head and retry), finish and UAT use the sandbox dir; read-only and merge stages keep trimmed detached worktrees from newWt (the branch parameter stays for the merge stage).

## Why

The script owns the dir, port and DB as structured facts and fails a ticket before any expensive agent starts. Read-only stages need no environment, so a sandbox for them would only hold ports and add setup time.

## Consequences

Supersedes only decision 1 of ADR 0002 ('each agent creates its own worktree'); decisions 2 to 6 stay. One extra cheap agent call per ticket. Tests that pin worktree-add prompt text change. Docs that mention per-stage worktrees change.

## How to reverse

Remove stageProvision and SANDBOX_SCHEMA, restore newWt with -b in stageImplement and the finish and UAT newWt calls, restore the RULES and head() text, revert the 0002 note, delete ADR 0100.
