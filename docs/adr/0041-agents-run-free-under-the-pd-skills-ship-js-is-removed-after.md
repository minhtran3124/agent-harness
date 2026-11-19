---
ticket: free-agents
stage: design
status: accepted
confidence: medium
decided_by: owner (2026-11-19)
date: 2026-11-19
---

# 0041. Agents run free under the pd skills; ship.js is removed after a control trial

## Context

ADR 0039 showed 0 skipped steps for free bug sessions. ADR 0040 kept ship.js for features only because its trial had no UAT and no depth L ticket, although free sessions matched ship.js on every hidden oracle at about a third of the uncached tokens. A read-only comparison of v4.0.0 with main found that v4 enforced order (lane gates, a run-state machine) but had no guard on irreversible actions, and that its best mechanism was end-state evidence: re-running claimed checks and a review receipt pinned to the reviewed commit. A read-only study of podbay-kit found three ideas worth taking (ideas only, the kit has no license): a short orchestrator skill for Pod Bay sessions, one shared isolated reviewer prompt with a round limit, and a time budget per ticket. On 2026-11-19 the owner decided to free the agents for bug and feature tickets, to let agents message each other directly across Pod Bay workspaces, to check evidence both by a reviewer and by a script, to add a Fable 5.2 advisor session for problems the Opus orchestrator cannot solve, and to prefix the new skills with pd. This ADR supersedes ADR 0040 and changes the bug brief of ADR 0039, so its revisit condition applies: the phase 2 trial measures the bug lane again.

## Options

- Free agents with an outcome contract, an isolated reviewer and an end-state check; ship.js removed after a trial that uses it as the control (chosen).
- Remove ship.js first and run the trial afterwards. Rejected: the trial loses its control group, and for a time no mechanical evidence check exists.
- Keep ship.js for depth L only. Rejected by the owner: two paths stay, and a wrong depth sends a ticket down the wrong one.
- Keep ship.js as an optional tool. Rejected by the owner: 2172 lines stay to maintain.
- Messages only through the orchestrator. Rejected: the orchestrator relays every review round and its context fills.
- A shared board that agents poll. Rejected: no signal when work ends, and write conflicts.

## Decision

Rules fall into three groups. Safety rules (merge, force-push, secrets, weakened tests) stay hard blocks in hooks and settings. Evidence is checked on the end state of a ticket. The order and method of work are no longer enforced: skills are a toolbox and each agent chooses. Four skills hold the roles: harness:pd-orchestrate (the main session on Opus 5.5 triages, asks the owner, has the blind acceptance tests of a feature written before the worker starts, assigns, routes review and acceptance checks, runs the evidence check, pushes and opens one pull request per ticket), harness:pd-work (a free worker session per ticket), harness:pd-review (a different session that re-runs the tests in its own worktree, runs the security review of a risky ticket, and returns a receipt pinned to the head commit; Opus 5.5 during the trial) and harness:pd-advise (a Fable 5.2 session in its own workspace that researches a problem the orchestrator could not solve after its own attempt and one Opus advisor round, and returns a solution; the orchestrator stays the decider). The protocol in skills/pd-orchestrate/references/protocol.md fixes the message envelope and types, the receipt, the worker report v2, the ledger that only the orchestrator writes, and the outcome contract per ticket kind. Workers and reviewers message each other directly for at most 3 rounds, then escalate. scripts/fleet-check.sh runs fixed checks in throwaway worktrees (repro red on the base and green on the head, full suite, receipt and report pinned to the head, acceptance tests changed only by the commits the orchestrator names and committed before any code, a security receipt for a risky ticket) on a private copy of the commits, so the worker's refs, config and hooks cannot change the result, and never runs a command taken from an agent's file; it starts in warn mode. Delivery has three phases, one pull request each: (1) this ADR, the skills, the protocol and fleet-check; (2) a trial on one machine with bug and feature tickets, one at depth L and one with real UAT, with ship.js outside local mode as the control; (3) removal of ship.js, the autopilot skill (its plan_groups.py moves to pd-orchestrate), the board and run_report.py, and release 6.0.0. Phase 3 waits for a new owner decision if the trial shows the free path worse on a measured axis.

## Why

Two trials showed that agents keep the steps without a script, at lower cost; what failed in them was evidence (a done claim before the review result), not order. v4 measured the same: its order gates fired on most commits and carried almost no information, while its evidence checks caught real gaps. A reviewer catches what a script cannot judge, and a script catches what a reviewer may skip. The trial runs before the removal because ADR 0040 named exactly the missing data: UAT and depth L.

## Consequences

Every ticket has one path, and the plugin becomes skills, agents and hooks. The orchestrator does more (acceptance checks, pull requests, the ledger); the direct review channel keeps its context small. Until phase 3 both paths exist: /harness:autopilot is unchanged and the pd skills are new. Not carried over from ship.js: the out-of-scope boundary check (the reviewer's intent check covers it), the feat/<slug> integration branch, the live board, and per-stage model profiles. fleet-check may move to block mode only by a later ADR, after the trial shows no false mismatch. Sessions on another machine are outside this design: Pod Bay gives no idle notice across machines.

## How to reverse

Before phase 3: delete the four pd skills and fleet-check.sh; nothing else depends on them. After phase 3: revert the deletion pull request, which restores ship.js and autopilot, and mark ADR 0040 accepted again.
