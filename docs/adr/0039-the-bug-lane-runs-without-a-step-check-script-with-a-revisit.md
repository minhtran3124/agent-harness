---
ticket: run
stage: design
status: accepted
confidence: medium
decided_by: owner (2026-11-19)
date: 2026-11-19
---

# 0039. The bug lane runs without a step-check script, with a revisit trigger

## Context

Bug tickets can run as free Pod Bay sessions: one worker per ticket, a brief with five steps (failing repro test, fix plus full suite, review by another session, local commit, report JSON with the marker `<!-- harness-fleet:report v1 -->`), and no ship.js workflow. A step-check script was proposed to check the end state of each ticket. The owner set the rule on 2026-11-19: run a trial; 0 skipped steps in total means no script for the bug lane, 1 or more means a small end-state check script. The trial ran on 2026-11-19 on machine U0 from base e66da56 with five tickets: four seeded bugs (three past fixes reverted, one seeded line) and one control ticket that is not a bug. Workers got only their ticket text and branch. Review ran in a separate session.

## Options

- Drop the script and record a revisit trigger (chosen).
- Drop the script with no trigger. Rejected: the evidence is five tickets, one run, workers on Opus 5.5 only.
- Build a small end-state check script anyway. Rejected: it goes against the rule the owner set before the trial, and it adds a script to maintain; an end-state check also cannot see step order, the one deviation the trial found.

## Decision

The bug lane runs without a step-check script. Feature tickets keep ship.js until a similar trial exists for them. Revisit (rerun the trial, or build the small end-state check) when any of these happens: a bug-lane worker skips a required step; bug-lane workers move to another model, for example Sonnet 5.5; or the brief's steps change.

## Why

Skipped steps in total: 0 of 5 tickets. The orchestrator checked each claim on its own rather than trusting the reports. The oracle tests (the tests of the original fixes at e66da56; for the seeded bug, the existing test extended to release-2.0 and production) failed on every trial branch and passed on the worker branches for 3 of 4 bugs; the fourth passed 16 of 17, and its failing case is a second bug that the ticket did not describe. The full suite passed on every worker branch. All 5 reports had the marker and valid JSON with every field. Main was unchanged and nothing was pushed. On the control ticket the worker changed no code and reported blocked with REPRO_NOT_FAILING and evidence. Review by the other session found a real regression in one fix and stale docs in another; both workers fixed them.

## Consequences

No new script or workflow. The orchestrator's checks before it reports a ticket done carry more weight: it must rerun the worker's new test on the base branch to confirm the test fails there, and must run the full suite on the worker branch, because the report alone is the worker's own claim. Known limits of the evidence: a small sample; workers ran Opus 5.5; in one ticket the orchestrator reminded the worker to address a review finding; 3 of 4 workers committed before they asked for review (no step was skipped, but the order differed from the brief).

## How to reverse

Build the small end-state check script (failing test seen on the base branch, full suite green, review by another session, commit on fix/<ticket>, valid report JSON), run it for each bug-lane ticket, and mark this ADR superseded.
