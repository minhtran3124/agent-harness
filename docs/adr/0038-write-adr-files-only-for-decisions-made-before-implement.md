---
ticket: 653
stage: design
status: accepted
confidence: high
decided_by: owner (2026-11-18)
date: 2026-11-18
---

# 0038. Write ADR files only for decisions made before implement

## Context

`write_adrs.py` wrote an ADR file for every decision with `adr: true` and two real options, whatever
stage made it. A choice an agent made while it coded, reviewed or fixed became a durable record
written after the code existed, so the record explained the code instead of guiding it. The owner
decided on 2026-11-18 that an ADR file is created only before a ticket is implemented.

## Options

- Only a decision from a stage before implement gets a file: an exact list of early stages
  (`intake`, `grilling`, `intent`, `research`, `design`, `plan`, `plan-review`), checked in
  `write_adrs.py` and mirrored in `ship.js` `takeDecisions` (chosen).
- Today's rule: any stage writes a file. Rejected: a file written after the code exists explains
  the code instead of guiding it.
- Write and commit the ADR file before the implement stage starts (#570). Rejected for now: it moves
  the ADR stage and the commit point; it can build on this rule later.

## Decision

An ADR file is written only for a decision with `adr: true`, two or more real options and a `stage`
that matches one of the early stages exactly, ignoring case and surrounding spaces. A decision that meets the rest of the rule but has
another stage, or no stage, is a late decision: no file, the `## Decisions` table row says
`late decision, no file`, and `needs_review` is forced true, so the PR body lists it under
`## Needs your decision`. This holds for an `owner_confirmed` late decision too: the ticket allows no
exception. When duplicates merge, an early `adr` item wins over a later one.

In `ship.js`, a call whose stage label is not early records its own label as the decision's stage,
so an agent in a late call cannot claim an early stage. `ADR_WHEN` and the stage rules state the
rule. `write_adrs.py --needs-out FILE` writes the `## Needs your decision` list for a manual run;
`ship.js` does not pass it, because `buildBody` already renders that list.

## Why

- The owner's rule of 2026-11-18: an ADR is created only before a ticket is implemented.
- The stage labels in `ship.js` are exact strings, and every label after implement differs from the
  early ones (`implement`, `review`, `review-fix`, `intent-fix`, `qa`, `attach`, `suite-fix`, `adr`,
  ...), so an exact match is enough. A prefix match would make `intent-fix` early.
- The ticket gate and the PR body read the in-memory decisions in `ship.js` before the ADR stage
  runs, so the forced `needs_review` must also happen there, not only in `write_adrs.py`.

## Consequences

- Fewer ADR files. A late decision lives only in the PR body after the merge.
- A late `adr` decision fails the ticket gate on `needs_review`; on a `feat/*` base the advisor
  judges it (#650).
- A later stage that restates an early decision still forces `needs_review` in memory, even though
  the merged early item gets its file.
- `qa` runs before implement but is not in the list, so its `adr` decisions are late. `intake`,
  `grilling` and `plan-review` never reach `takeDecisions` in `ship.js`; they matter for manual and
  `/harness:compound` input. Adding a label is a one-line change in both lists.
- A `/harness:compound` decision with a stage after implement now gets no file either.

## How to reverse

Remove `EARLY_STAGES` and the late branch from `write_adrs.py` (`needs_adr` returns the plain ADR
rule), drop `--needs-out`, revert the `ADR_WHEN`, `rulesDecisions` and `takeDecisions` changes in
`ship.js` and the harness case `ad1`, restore the doc sections, and mark this ADR superseded.
`git revert` of the merge commit does all of it.
