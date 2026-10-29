---
ticket: 477
stage: design
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: design)
date: 2026-10-29
---

# 0130. runId is the slug of the run, so a resume reuses the same sandbox

## Context

provision-sandbox.sh needs a runId and ship.js has none. The sandbox dir is <parent>/.ship-<repo>/<runId>-t<n>-<slug>.

## Options

- RUN_ID = slugOf(slug), stable across a resume
- Random or timestamp runId per start

## Decision

Use RUN_ID = slugOf(slug).

## Why

A stable id lets a re-run find its own sandbox instead of creating a second one with a new port block, and makes the clean --run command printable in the end-of-run log.

## Consequences

Two concurrent runs with the same slug on the same repo would share sandbox names; the script's own refusal then blocks the second ticket with a clear message.

## How to reverse

Pass a timestamped runId in args or derive it at start.
