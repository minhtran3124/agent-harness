---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix); text corrected to match the code at the owner's request
date: 2026-10-29
---

# 0009. A FAIL row fails UAT; console errors are report-only

## Context

The UAT schema returns `passed_ac`, `scenarios[]` and `console_errors`. The first review round found that nothing checked these: an AC row with FAIL, or console errors, could still pass. The first fix also made any console error fail UAT. The second review round found that this blocks a ticket whose ACs all pass because of unrelated console noise, and reverted that part.

## Options

- Treat any console error greater than 0 as an AC failure
- Fail on `passed_ac` not exactly true or on an AC row with FAIL; report console errors only

## Decision

`uatOk` in `ship.js` passes only when `passed_ac === true` and no scenario with `kind: 'ac'` has status FAIL. `console_errors` never fails a run, and the `uat-fix` prompt does not ask the agent to fix console errors.

## Why

The agent's `passed_ac` is a claim, so the scenario rows must agree with it. Console errors that no AC depends on are noise for acceptance and must not block a ticket (test u5d).

## Consequences

Console errors show in the UAT report only. An AC that a console error breaks still fails through its own FAIL row.

## How to reverse

Add a `console_errors` clause to `uatOk` in `ship.js`, and update tests u5d and u5f.
