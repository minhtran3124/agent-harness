---
ticket: 476
stage: implement
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0128. Process group via set -m, killed after every check

## Context

macOS has no setsid; the group must be killed on exit.

## Options

- set -m job control with kill of -pgid
- setsid

## Decision

set -m in the script; kill the group on timeout and also after the check ends.

## Why

Portable on ubuntu and macOS; stops leaked background servers.

## Consequences

A check cannot leave a daemon running after provisioning.

## How to reverse

Drop the post-exit kill in run_check.
