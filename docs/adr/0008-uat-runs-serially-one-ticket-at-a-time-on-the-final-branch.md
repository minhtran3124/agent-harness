---
ticket: 462
stage: research
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: research)
date: 2026-10-29
---

# 0008. UAT runs serially, one ticket at a time, on the final branch

## Context

Several FE/BE tickets share one final branch and would start the app on the same port.

## Options

- serial per ticket in input order
- parallel per ticket

## Decision

Run UAT serially per ticket, each in its own worktree on finalRef.

## Why

Avoids port clashes and matches the serial fix rounds the owner chose.

## Consequences

Longer run for multi-ticket ships.

## How to reverse

Run the stage in parallel with a port per ticket.
