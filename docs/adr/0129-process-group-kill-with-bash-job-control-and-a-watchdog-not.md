---
ticket: 476
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0129. Process-group kill with bash job control and a watchdog, not setsid or timeout

## Context

A check may start the app in the background. The owner asked for a 60 s timeout and a process group kill on exit. macOS has neither `timeout` nor `setsid` by default, and CI runs on ubuntu and macOS.

## Options

- bash `set -m` plus a watchdog and `kill -- -PGID`
- GNU timeout or setsid
- python or perl helper

## Decision

Use bash `set -m` plus a background watchdog.

## Why

It needs no extra tools and works on both CI platforms.

## Consequences

Slightly more shell code; a test overrides the timeout through an internal variable.

## How to reverse

Replace the runner function with `timeout` or `setsid`.
