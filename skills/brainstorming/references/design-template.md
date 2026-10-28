# Design template

Write `specs/<slug>/design.md` (depth L only). Keep each section short; drop one that has nothing to say.

```text
# <slug> — Design

Written <YYYY-MM-DD>. Pins: <repo short sha the claims were checked against>

## Goal
One or two sentences.

## Current state
What exists today that the change builds on, with file pointers.

## Approaches considered
Two or three options, their trade-offs, and the chosen one.

## Design
Components, data flow, interfaces, error behavior.

## Tests
What proves it works: commands and expected results.

## Non-goals
What this change does not do.

## Decisions
Choices made and why (in auto mode these are the decisions[] entries).
```
