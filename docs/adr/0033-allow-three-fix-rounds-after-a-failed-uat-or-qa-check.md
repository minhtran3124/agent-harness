---
ticket: 619
stage: design
status: accepted
confidence: high
decided_by: owner
date: 2026-11-11
---

# 0033. Allow three fix rounds after a failed UAT or QA check

## Context

When UAT or the qa-verifier found a failed acceptance criterion, `ship.js` ran one fix agent and one rerun. If the AC still failed, the ticket was blocked and waited for the owner. One round was often too few, and nothing recorded which commit the check ran on.

## Options

- Keep one fix round.
- Allow up to 3 fix rounds, each followed by a rerun, with one advisor call before round 3.
- Loop until the check passes, with no cap.

## Decision

Add `MAX_QA_FIX_ROUNDS = 3` and one loop in `stageUat` that serves UAT and the qa-verifier. Each fix and each rerun has its own worktree. Round 3 gets one advisor call, and its advice goes into the fix prompt only, so the check stays plan-blind. The loop stops when a fix lands no commit or a rerun cannot run. After the loop, a fix commit that touches the acceptance tests blocks the ticket. The record keeps the head SHA of the last check, and the PR body prints 7 characters of it. A failed `docs` ticket is blocked with reason `QA check AC failed`.

## Why

Two or three rounds fix most failures that the first fix misses; the cap bounds cost. The advisor sits before the last round, where a new view helps most. An uncapped loop can spend without end.

## Consequences

Enables: more failed checks end as passed without the owner. Costs: up to 3 fix agents, 3 reruns and one Opus advisor call per failed ticket (before: 1 and 1); each rerun of an app ticket is a browser run. Up to 3 fix commits reach the integration branch with no second code review; the full suite still runs after this phase. A run with no failed check does not change.

## How to reverse

Set `MAX_QA_FIX_ROUNDS` to 1. The advisor call then never runs.
