---
ticket: 653
stage: design
status: accepted
confidence: high
decided_by: claude (ship workflow: design)
date: 2026-11-18
---

# 0037. Write ADR files only for decisions made before implement

## Context

write_adrs.py writes an ADR file for any adr:true decision with two options, whatever stage made it, so a choice made while coding, reviewing or fixing becomes a record written after the code exists. The owner decided on 2026-11-18 that an ADR file is created only before a ticket is implemented.

## Options

- Exact early-stage list (intake, grilling, intent, research, design, plan, plan-review) checked in write_adrs.py and mirrored in ship.js takeDecisions; a late or stage-less adr:true decision gets no file, needs_review true and the table cell `late decision, no file`
- Keep today's rule: any stage writes a file
- Write and commit the ADR file before the implement stage starts (#570)

## Decision

Use the exact early-stage list in both write_adrs.py (file gate, forced needs_review after dedupe, table cell, new --needs-out list) and ship.js (ADR_WHEN, rulesDecisions, takeDecisions forces needs_review and pins a late caller's stage).

## Why

It is the owner's rule; takeDecisions always fills stage so the ship.js mirror is exact; the script check covers manual and stage-less input; ship.js labels after implement are all distinct from the early labels, so an exact match is safe while a prefix match would make intent-fix early.

## Consequences

Fewer ADR files; a late decision fails the ticket gate on needs_review and lives only in the PR body after the merge; a new early stage label must be added to both constants.

## How to reverse

Remove EARLY_STAGES and the late branch from write_adrs.py, drop --needs-out, revert ADR_WHEN, rulesDecisions and takeDecisions in ship.js and the harness assertions, restore the doc sections, mark the ADR superseded.
