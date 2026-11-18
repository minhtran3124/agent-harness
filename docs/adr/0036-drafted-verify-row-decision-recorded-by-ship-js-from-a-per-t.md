---
ticket: 648
stage: implement
status: accepted
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-11-18
---

# 0036. Drafted Verify: row decision recorded by ship.js from a per-ticket verifyDrafted flag

## Context

The design sent the --no-ask drafted-row decision as an open question in confirmed. The advisor found that this is not reliable: every stage gets head(), and takeDecisions does not remove duplicates. The decision gates the per-ticket auto-merge.

## Options

- Open question in confirmed; the model records it (design option A)
- Optional per-ticket boolean verifyDrafted; ship.js calls addDecision exactly once when noAsk is set (advisor fix, partly reverses rejected option C)

## Decision

Added optional ticket field verifyDrafted (validated as a boolean). When NO_ASK is set and the flag is true, runTicket records exactly one decision, 'Verify: row drafted for #<n>', with needs_review true. SKILL.md step 6 sets the flag. launch-args.md documents it. Test pf4 covers it.

## Why

The merge gate becomes deterministic: no missed or duplicated decision. A boolean is a small contract.

## Consequences

The ship.js launch args gain one optional per-ticket field. In --no-ask runs, a ticket with a drafted row is never auto-merged into feat/<slug> until the owner reviews it.

## How to reverse

Remove the verifyDrafted check in validateArgs and the addDecision block at the start of runTicket. Drop the field from SKILL.md step 6 and launch-args.md, and delete pf4.
