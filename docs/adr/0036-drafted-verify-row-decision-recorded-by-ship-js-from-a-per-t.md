---
ticket: 648
stage: implement
status: accepted
confidence: high
decided_by: claude (ship workflow: implement), revised by the owner-approved hand fix
date: 2026-11-18
---

# 0036. Drafted Verify: row decision passed by the skill and normalized by ship.js

## Context

Under `--no-ask`, a ticket whose `Verify:` row the autopilot skill drafted must carry a `needs_review` decision titled
`Verify: row drafted for #<n>`. The design first sent it as an open question in `confirmed`. The advisor found that
unreliable: every stage gets `head()`, and `takeDecisions` does not remove duplicates. The decision gates the per-ticket
auto-merge, so it must be recorded exactly once.

## Options

- Open question in `confirmed`; the model records it (design option A)
- Optional per-ticket boolean `verifyDrafted`; ship.js builds the decision when `noAsk` is set
- Optional per-ticket `decisions` list that the skill fills; ship.js records each entry once and normalizes it

## Decision

The third option. The issue says the skill passes the decision, and intent review flagged the boolean as drift from
that. ship.js keeps only the text fields of each entry (`title`, `context`, `decision`, `why`, `consequences`,
`how_to_reverse`) and always records it with `needs_review: true`, `adr: false`, `owner_confirmed: false` and the
ticket's own number, so an entry can never clear the review flag or ask for an ADR file. Tests pf4 and pf7 cover it.

## Why

The merge gate stays deterministic: one decision per entry, recorded by the script, and no field the caller sets can
weaken it.

## Consequences

The launch args gain one optional per-ticket field, used only with `--no-ask`. A ticket with a drafted row is not
auto-merged into `feat/<slug>` until the owner reviews the row.

## How to reverse

Remove the `decisions` check in `validateArgs`, `skillDecision` and its loop at the start of `runTicket`. Drop the
field from SKILL.md step 6 and `references/launch-args.md`, and delete pf4 and pf7.
