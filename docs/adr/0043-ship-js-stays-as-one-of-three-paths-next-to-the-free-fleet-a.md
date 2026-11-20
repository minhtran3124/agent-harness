---
ticket: keep-ship-js
stage: design
status: accepted
confidence: medium
decided_by: owner (2026-11-20)
date: 2026-11-20
---

# 0043. ship.js stays as one of three paths next to the free fleet and a single agent

## Context

ADR 0041 planned three phases: the pd skills (phase 1), a trial with ship.js as the control (phase 2), and the removal of ship.js, the autopilot skill, the board and run_report.py with release 6.0.0 (phase 3), unless the trial showed the free path worse on a measured axis. The trials ran on 2026-11-19 and 2026-11-20. Trial p2 (five tickets per group, hidden oracles): the free fleet finished 5 of 5 and ship.js 2 of 5; ship.js blocked one ticket whose oracle passed and then skipped its two dependents. In input-equivalent tokens (cache reads included) the fleet cost about 10.7M against 7.3M for ship.js, about 2.1M against 3.6M per finished ticket, and the fleet orchestrator session alone was about 58% of the fleet's cost (estimates, specs/routing-research/report.md in the research workspace). Trial p3 ran one depth L ticket (#680) through the fleet with a Fable advisor session. The earlier ADR 0040 trial had ship.js match free sessions on four independent tickets. A routing study (2026-11-20) found each path strong in a different place: ship.js for batches of independent, ready, low-risk tickets and for runs with no owner present; the fleet for owner questions mid-run, dependent tickets, recovery and high-risk work; a single agent for small low-risk work. On 2026-11-20 the owner decided to keep ship.js and let the orchestrator choose the way of working per ticket from four questions: is the work complex enough, is it worth the money, can an agent do every stage, and is a mistake expensive and hard to see.

## Options

- Keep ship.js as one of three paths (ship.js, free fleet, single agent), chosen per ticket, with the same end-state evidence check after every path (chosen).
- Remove ship.js as phase 3 of ADR 0041 planned. Rejected by the owner: ship.js runs unattended batches with no orchestrator context to pay for, and the trial measured that orchestrator as the largest single cost of the fleet.
- Keep ship.js for depth L only, as ADR 0041 had listed and rejected. Rejected: the trials point the other way (depth L and dependent tickets went better in the fleet; ship.js did well on independent tickets), and depth alone was misjudged once (#688).

## Decision

Phase 3 of ADR 0041 is cancelled: ship.js, the pd-autopilot skill, the board and run_report.py stay, and no 6.0.0 removal release follows. The rest of ADR 0041 stands: the pd skills, the protocol, the outcome contract and fleet-check. There are three ways to run a ticket: ship.js (launched by /harness:pd-autopilot), the free fleet (/harness:pd-orchestrate) and a single agent. The orchestrator chooses one per ticket from the owner's four questions; until a tested routing rule exists, it records the choice and its reason, and an owner label or answer overrides it. The goal is one end-state check for every path: the evidence of the outcome contract (protocol.md) checked on the head commit. Today `fleet-check.sh` reads only what the fleet writes (a review receipt and a v2 report), so it checks the fleet path alone; ship.js keeps its own gates and the single agent is checked by its reviewer agent and the suite. Making the ship.js and single-agent paths write the same receipt and report, so that fleet-check runs after them too, is required work before either path is used without the owner watching. A ticket may move to a heavier path during a run, never to a lighter one.

## Why

The trials did not show one path better everywhere: ship.js matched the free sessions on independent tickets (ADR 0040) and failed on a dependent batch (trial p2), while the fleet finished every ticket at a higher total cost driven by its orchestrator. Keeping the cheaper fixed path for the work it fits, and the flexible path for the rest, costs less than forcing one shape on every ticket. Once every path ends in the same end-state check, the objection ADR 0041 raised against two paths falls away: a wrong route then costs tokens or a second attempt, not a wrong merge. Until then that guarantee holds for the fleet path only.

## Consequences

Two entry points stay supported and tested; ship.js keeps its tests and its board. ship.js and the single-agent path must learn to write the fleet's review receipt and v2 report, or fleet-check must learn their outputs, before the shared check covers them. A routing rule is now needed: the research proposes a decision table, a shared risk definition, a depth rule in pd-intake and a route record with its reason in the ledger, each to land in its own PR. The single-agent path has no trial evidence yet and needs one before it becomes a default. Thinning the fleet orchestrator becomes the main cost lever. Issues that assumed the removal of ship.js or the board (for example #654, #643, #631) stay open.

## How to reverse

Write an ADR that restores phase 3 of ADR 0041 and remove ship.js, the pd-autopilot skill, the board and run_report.py in one pull request.
