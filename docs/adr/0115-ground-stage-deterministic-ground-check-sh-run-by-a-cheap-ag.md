---
ticket: 521
stage: design
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: design)
date: 2026-10-30
---

# 0115. Ground stage: deterministic ground-check.sh run by a cheap agent, with a one-re-run gate in ship.js

## Context

Ticket #521 (depth L): research, design and plan claims reach implement without anyone checking them against the code. ship.js cannot run a shell; stages read integRef (ship.js:195). runStage (ship.js:310), askAdvisor (ship.js:298), Blocked (ship.js:296) exist. Pins: 0e42a7f2, 2026-10-30.

## Options

- A: bash script plugins/harness/scripts/ground-check.sh (git cat-file/show/grep on integRef) run by a haiku agent; ship.js judges exit code; (new) text marker
- B: LLM reviewer agent reading text and code
- C: new_files schema field instead of a text marker

## Decision

Option A. ground-check.sh --repo --ref --mode full|paths-only FILE...; exit 0/1/2; one 'FAIL <kind>: <claim> (<reason>)' line per failure; it checks path:line citations (with a quote within N-2..M+2), backtick paths, code-like backtick symbols, Done-when command paths, and Pins ancestry; (new) after a token exempts it everywhere in the text set. The stageGround agent writes the texts to wtRoot/ground-<n>/ and runs the script. groundGate re-runs stageDesign/stagePlan once through a new optional ground-advice argument; a second failure calls askAdvisor, adds a needs_review decision and throws Blocked before implement. Depth L: full check on research+design after design (the second check covers the design only), paths-only on the plan after plan; depth M: paths-only on the plan; depth S unchanged.

## Why

Deterministic and cheap, follows the integRef rule, and reuses build(advice), askAdvisor, addDecision and Blocked; the text marker works for all three stage texts and humans can see it.

## Consequences

Two extra haiku calls per L ticket and one per M ticket; failures cost one stage re-run; the shellcheck count test changes from 9 to 10; the harness gets ground defaults and cases; the templates and stage prompts teach (new) and path:line citations.

## How to reverse

Remove the groundGate calls in runTicket and the helper code, delete the script and its test, set the shellcheck count back to 9, and revert the docs and template lines.

## See also

- 0122: codegraph is an optional helper for the research stage, not a ground check.
