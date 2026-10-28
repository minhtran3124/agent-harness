---
ticket: 398
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0047. Table output reaches the PR body through a new --table-out flag

## Context

The CLI --input prints a JSON list of written ADRs, and --render-section builds the body from that list. The table must also list decisions that have no file, which the written list cannot hold.

## Options

- Add --table-out FILE to the --input run and let the ADR stage put that file into the body
- Change the --input stdout shape to an object with adrs and rows
- Pass the full decisions file to --render-section a second time

## Decision

Add --table-out FILE (markdown table of all deduped decisions); keep stdout as the list of written ADRs.

## Why

Keeps the stdout contract that ship.js and existing tests read, and keeps all logic in the script as the owner asked.

## Consequences

The ADR stage prompt gains one flag. Old callers that omit it get the old behaviour minus filtered-out files.

## How to reverse

Remove the flag and render the table from the written list.
