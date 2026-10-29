---
ticket: 462
stage: implement
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0080. UAT AC failure marks the ticket blocked in run output

## Context

After one fix round and one rerun, an AC still failing sets the ticket status to blocked with reason 'UAT AC failed'.

## Options

- Mark blocked, keep code, PR opens
- Keep ticket done and only record a decision
- Revert the code

## Decision

Mark the ticket blocked with reason 'UAT AC failed'; the code stays and the PR still opens. This flips Closes #n to Refs #n in the PR body and changes out.tickets[].status.

## Why

Owner-confirmed: an AC failure fails the ticket, no revert. The advisor asked for the effect on the output contract to be recorded.

## Consequences

Consumers of the run output see a blocked ticket whose PR exists; the final PR body says Refs instead of Closes.

## How to reverse

Remove the r.status/r.reason assignment in stageUat in ship.js.
