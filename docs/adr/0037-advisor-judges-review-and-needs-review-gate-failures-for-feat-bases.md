---
ticket: 650
stage: design
status: accepted
confidence: high
decided_by: owner (ticket #650, and the 2026-11-18 answer on accepted needs_review decisions)
date: 2026-11-18
---

# 0037. Advisor judges review and needs_review gate failures for feat/* bases

## Context

The ticket gate in `ship.js` (`stageGate`) sends a ticket to a human merge when one review finding with a score of 50
or more is left, or when the ticket has one open `needs_review` decision. The ticket is then missing from the integration
branch and every dependent ticket is skipped. In real runs this stopped whole milestones on an integration branch,
where nothing reaches `main` without the owner.

## Options

- Keep blocking: every leftover finding and every `needs_review` decision stops the ticket.
- Advisor judges: on a run base that matches `feat/*`, when the gate failed only on review findings or `needs_review`
  decisions (CI green, intent `match`, no failed security gate, no `dangerous` or `contradicts_confirmed` decision),
  ask the advisor once for a verdict per item: `accept`, `fix` (one more fix round, then the gate again with no second
  advisor call) or `owner`.
- Raise the review threshold, or let the final PR gate accept items.

## Decision

Advisor judges. The call fails closed: no answer, or an unclear one, means `owner`. Each accepted item is recorded as an
`Accepted by advisor: ` decision and listed under `## Accepted by advisor` in the final PR body. An accepted or fixed
`needs_review` decision keeps `needs_review`: only the ticket gate sets it aside, so the final PR stays a human merge and
still lists the decision under `## Needs your decision` (owner, 2026-11-18). `decideFinalMerge` and `merge-guard.sh`
do not change.

## Why

A milestone on an integration branch can finish without the owner next to it, and the owner still sees every item the
advisor let through before anything reaches `main`.

## Consequences

- A ticket gate failure on a `feat/*` base costs one advisor call, and at most one fix round, one re-review and one
  intent review.
- A run whose base is `main` (the integration branch is then only the ticket PR base) gets no advisor gate: the base
  test reads the run base, as the ticket's acceptance criteria require.
- Accepted review findings reach the final PR; the owner reads `## Accepted by advisor` before the merge.

## How to reverse

Remove the advisor block, `askGate` and `ADVISOR_GATE_SCHEMA` from `stageGate` in `ship.js`, the `## Accepted by advisor`
section in `buildBody`, and the ga and gav cases in `tests/workflows/harness.js`.
