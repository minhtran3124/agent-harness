---
ticket: 443
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0078. Visibility of the first log line in /workflows is not verified

## Context

The owner asked to check where log() lines show in /workflows and note the limit if the first line is not visible there.

## Options

- Verify in the UI
- Note the limit

## Decision

Not verified; the shorter description is kept and the limit is noted here.

## Why

The ticket marks how /workflows displays title and log lines as out of scope, and there is no UI in this headless run.

## Consequences

The first log line is covered only by the stubbed test.

## How to reverse

Check the /workflows UI manually.
