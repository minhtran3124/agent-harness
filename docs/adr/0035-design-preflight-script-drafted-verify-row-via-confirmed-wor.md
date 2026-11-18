---
ticket: 648
stage: design
status: accepted
confidence: high
decided_by: claude (ship workflow: design)
date: 2026-11-18
---

# 0035. Design: preflight script, drafted Verify row via confirmed, worktreeSetup in newWt prompt text

## Context

Runs found missing setup mid-run (no Verify: row, missing system package, specs/ not ignored); ship.js has no shell and newWt only runs git worktree add.

## Options

- A: preflight.sh run by the skill; worktreeSetup appended to the newWt prompt text; drafted Verify row through the existing confirmed/noAsk channels
- B: a separate setup stage per worktree
- C: new launch-arg fields for drafted rows and preset decisions
- D: checks inside ship.js or an agent

## Decision

Option A: read-only preflight.sh with `missing: <name>` lines run in SKILL step 1; validated worktreeSetup list (args and profile) appended as its own block after the newWt paragraph; rulesCore dependency/no-sudo line; drafted Verify row passed in confirmed, with stageVerify told to use it when the body has none.

## Why

No extra agent cost, reuses head()/noAsk/stripVerify, adds only one optional arg to ship.js, and catches setup problems before triage.

## Consequences

Every worktree-creating stage runs the setup commands when set; ship.js gains one optional arg and one rules line; SKILL.md depends on the exact preflight strings.

## How to reverse

Delete preflight.sh and its test, revert the SKILL.md, ship.js, load_profile.py and reference doc edits, remove pf1-pf3.
