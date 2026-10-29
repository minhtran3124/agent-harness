---
ticket: 474
stage: intent
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: intent)
date: 2026-10-29
---

# 0125. Running means a live .sandbox.pid file; no PR number is stored at creation

## Context

The owner defined running as a live pid file but did not name the file or its format.

## Options

- <sandbox>/.sandbox.pid containing a pid, checked with kill -0
- flock-based lock file

## Decision

Use <sandbox>/.sandbox.pid holding one pid, live when kill -0 succeeds; a dead pid counts as not running. The pr field in .sandbox.json is null at creation, and list reads the PR state from gh.

## Why

It is simple, portable to macOS and ubuntu, and testable. ship.js can write the file in a later ticket.

## Consequences

Until something writes the pid file, no sandbox shows as running. The convention becomes a contract for ship.js.

## How to reverse

Change the liveness check in one function.
