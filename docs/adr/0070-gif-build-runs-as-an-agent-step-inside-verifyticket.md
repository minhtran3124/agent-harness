---
ticket: 414
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0070. GIF build runs as an agent step inside verifyTicket

## Context

ship.js is a workflow script and cannot run shell; ffmpeg must run through an agent. The verify result already carries stills and a gif: null placeholder.

## Options

- Separate cheap-model agent call (gif:<n>) in verifyTicket after the verify and base checks pass
- Make the verify agent build the GIF itself
- Build the GIF in the finish agent

## Decision

Separate cheap-model agent call labelled gif:<n>, run only for non-local pass or flaky results.

## Why

Keeps the verify agent to running and reporting, keeps the GIF failure from affecting the verify result, and is easy to stub in the harness.

## Consequences

One extra cheap agent call per verified ticket; gif path flows to the attach step through verifyResult.gif.

## How to reverse

Remove the gif agent call and return gif: null again.
