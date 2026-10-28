---
ticket: 382
stage: intent
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: intent)
date: 2026-10-28
---

# 0003. Edit five descriptions in this ticket, record it as an ADR

## Context

The ticket acceptance says 'all current skills and agents pass without editing any description; if one fails, report it'. With the owner-confirmed regex, 5 still fail: autopilot, diagnosing-bugs, finishing-a-development-branch, setup, implementer.

## Options

- Leave them and let the live-repo test and run-tests.sh fail
- Allowlist the five in the checker
- Add a minimal 'Use when ...' clause to each description

## Decision

Add one short 'Use when ...' clause to each of the five descriptions, as the owner confirmed. The ADR stage writes this deviation from the ticket text.

## Why

Owner-confirmed decision 2. An allowlist would hide real gaps, and a failing live-repo test breaks the acceptance item 'bash scripts/run-tests.sh passes'.

## Consequences

Five public skill and agent descriptions change, which changes how the model routes to them; the clause must not narrow or contradict the existing text.

## How to reverse

git revert the commit that edits the five files, or remove the added sentence from each description line.
