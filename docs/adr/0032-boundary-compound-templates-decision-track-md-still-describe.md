---
ticket: 567
stage: implement
status: needs-review
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-11-05
---

# 0032. Boundary: compound/templates/decision-track.md still describes a docs/solutions decision note

## Context

The compound decision track now writes ADRs. decision-consolidated.md is on the ticket's file list and was rewritten as the write_adrs.py input shape. templates/decision-track.md, the single-decision docs/solutions template, is not on the list.

## Options

- Edit or delete decision-track.md
- Leave it untouched and report it

## Decision

Left decision-track.md untouched. No skill file points at it any more.

## Why

The boundary says a change outside the named files is not made.

## Consequences

An unused template that describes the old decision note stays in the plugin until a follow-up removes it.

## How to reverse

Delete plugins/harness/skills/compound/templates/decision-track.md in a follow-up.
