---
ticket: run
stage: intent-fix
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-31
---

# 0134. ADR: record the ask probe and the owner-approved merge as updates to ADR 0108 and 0109, no new ADR file

## Context

AC6 asks for a new ADR that updates ADR 0108 and 0109. The rules say stage agents never write ADR files; the ADR stage writes new ones from decisions[].

## Options

- Append update sections to ADR 0108 and 0109 (both are named in the file set)
- Skip the ADR and only return decisions[]

## Decision

Appended an Update (ticket #545) section to ADR 0108 and ADR 0109 with the real probe result and the no-fallback decision. The new ADR file is left to the ADR stage through this decision entry.

## Why

The two files are in the allowed set and the update is the part of AC6 that this stage can do. The probe result must be recorded where a reader of the merge policy will look.

## Consequences

A reviewer sees the probe result in the ADRs. The probe covers headless -p only; the interactive prompt is not tested. The 0108 and 0109 front matter still says status needs-review.

## How to reverse

Remove the two Update sections.
