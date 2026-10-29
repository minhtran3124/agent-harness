---
ticket: 474
stage: plan
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: plan)
date: 2026-10-29
---

# 0126. Running means a live <sandbox>/.sandbox.pid; pr is null at creation

## Context

The owner defined running as a live pid file but did not name the file or format.

## Options

- <sandbox>/.sandbox.pid with one pid checked by kill -0
- flock-based lock file

## Decision

Use .sandbox.pid holding one pid, live when kill -0 succeeds; a dead pid is not running. list reads PR state from gh, not from the pr field.

## Why

Simple, portable to macOS and ubuntu, testable; ship.js can write it in a later ticket.

## Consequences

Until something writes the pid file, nothing shows running. The convention becomes a contract for ship.js.

## How to reverse

Change the liveness check in one helper function.
