---
ticket: 530
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-31
---

# 0130. UAT not run for #530

## Context

The UAT stage could not check the running app: No verify.config.json found. It is missing at .ship-agent-harness/530-spike-push-to-main-deny-rule/t530/verify.config.json and at the root of the uat-530 worktree. UAT rules forbid inferring or writing a config. The ticket is also a config/hook/doc change with no running app to start.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 530 by hand.
