---
ticket: 475
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0127. Read teardown lines from the repo manifest at clean time

## Context

Clean needs the teardown commands; they could come from the repo's .harness-sandbox now or from a copy stored at provision time.

## Options

- Read <repoDir>/.harness-sandbox at clean time
- Store teardown commands in .sandbox.json at provision time

## Decision

Read <repoDir>/.harness-sandbox at clean time.

## Why

clean already receives repoDir, and the manifest is the single source; no change to the .sandbox.json format.

## Consequences

If the manifest changes between provision and clean, the new teardown lines run.

## How to reverse

Record the lines in .sandbox.json at provision time and read them in clean.
