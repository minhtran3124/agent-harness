---
ticket: run
stage: design
status: superseded
superseded_by: 0041
confidence: medium
decided_by: owner (2026-11-19)
date: 2026-11-19
---

# 0040. Feature tickets keep ship.js until a second free-session trial with UAT and a depth L ticket

## Context

ADR 0039 dropped the step-check script for the bug lane after two trials. The owner then asked whether feature tickets also need ship.js. A trial ran on 2026-11-19 on machine U0 from main f138bfc3, with the harness plugin loaded from that commit and Sonnet 5.5 sessions. Five new feature tickets (F1 check-md-links GitHub annotations, F2 clean-worktrees dry run, F3 board /healthz, F4 release candidates, F5 a vague board-on-phone ticket as control) ran twice: group A as free sessions with an 11-step brief (docs/fleet/feature-lane-brief.md) and a separate review session, group B through /harness:autopilot and ship.js in local mode. Hidden oracle tests for F1-F4 were written by the orchestrator and checked against a reference implementation (fail on main, pass with the reference). The owner answered every intake and grilling question in both groups.

## Options

- Keep ship.js as the default for feature tickets until a second trial confirms the result (chosen).
- Drop ship.js for feature tickets now. Rejected: group B ran in local mode, where ship.js skips UAT, so the comparison is not like for like; no ticket reached depth L; one run of five tickets.
- Keep ship.js and stop testing free sessions. Rejected: group A matched ship.js on every oracle at about a third of the uncached tokens, which is worth confirming.

## Decision

ship.js stays the default for feature tickets. The free-session feature lane, with the brief in docs/fleet/feature-lane-brief.md, may be used for trials. A second trial runs before the decision is made: group B not in local mode so UAT runs, a verify config and a browser for UAT in both groups, and at least one depth L ticket and one real FE ticket. If group A again skips no required stage and matches ship.js on the oracles, the free lane becomes an accepted way to run feature tickets.

## Why

Group A skipped no required stage on any ticket, and every step left its artifact (intent, plan, blind acceptance tests committed before code, implementer subagents in worktrees, security review on F2 and F4, review by another session, qa-verifier on F1-F4, report JSON). In three tickets a step was done without the named skill (F3 wrote plan.md without writing-plans, F5 called the implementer agent without the implement skill, four tickets wrote decision.md without decision-record). Oracles: group A 4 of 4 tickets fully passed (12/12, 15/15, 7/7, 17/17), group B the same; the full suite passed on every branch. On the control ticket F5 both groups asked the owner before any code. Cost: group A used 3.2-8.1M tokens per ticket (177-470k uncached) and 7-14 minutes; group B 4.2-11.7M (760k-1.56M uncached) and 7-27 minutes. Limits: ship.js logged 'UAT skipped: local mode has no verify result' in group B; group A's UAT on F3 and F5 was blocked because the machine had no browser automation and no verify config; ship.js chose depth S for F1 and F3 and so, by its rules, ran no plan or blind tests there; both groups rated F4 depth M, so no depth L ticket ran; the autopilot skill in group B asked the go/no-go question before its step 7 summary on F5.

## Consequences

No change to ship.js or to the autopilot skill. docs/fleet/feature-lane-brief.md records the brief so the second trial can reuse it. The orchestrator of a free lane must route reviews to another session and check workers' claims, as in the bug lane. The UAT gap in local mode and the autopilot step-7 order are separate follow-ups.

## How to reverse

To adopt the free lane without a second trial, mark this ADR superseded by one that accepts it. To stop the free lane, delete docs/fleet/feature-lane-brief.md and mark this ADR superseded.
