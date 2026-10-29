---
ticket: 476
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-29
---

# 0105. UAT not run for #476

## Context

The UAT stage could not check the running app: Neither verify.config.json exists. It is missing at .ship-agent-harness-simplify/sandbox-per-ticket/t476/ and at the root of the uat-476 worktree (checked out from github/feat/sandbox-per-ticket). The UAT skill forbids inferring or writing a config. This ticket is also a shell script and manifest change with no web app to start.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 476 by hand.
