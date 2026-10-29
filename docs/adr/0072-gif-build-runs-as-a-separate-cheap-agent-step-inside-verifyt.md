---
ticket: 414
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0072. GIF build runs as a separate cheap agent step inside verifyTicket

## Context

ship.js cannot run shell; ffmpeg must run through an agent. The verify result already carries stills and gif: null.

## Options

- Separate haiku agent call gif:<n> in verifyTicket
- Verify agent builds the GIF
- Finish agent builds the GIF

## Decision

Separate haiku agent call labelled gif:<n>, only for non-local pass or flaky results, after the base check.

## Why

Keeps the verify agent to running and reporting, isolates GIF failure from the verify result, and is easy to stub.

## Consequences

One extra cheap call per verified ticket; the path flows to attach through verifyResult.gif.

## How to reverse

Remove the gif call and return gif: null.
