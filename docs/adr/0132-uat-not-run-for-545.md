---
ticket: 545
stage: uat
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: uat)
date: 2026-10-31
---

# 0132. UAT not run for #545

## Context

The UAT stage could not check the running app: No verify.config.json exists at /home/minhtran/Documents/agilityio/.ship-agent-harness/merge-approval-from-session/t545/verify.config.json. It is also not at the root of branch github/feat/545-let-the-owner-approve-a-merge-into-base-. The UAT skill forbids inferring or writing a config. Separately, `git fetch origin` failed (the remote is named `github`, not `origin`), so the uat-545 worktree was never created. The ticket changes a hook script and docs, and the repo has no web app to start.

## Options

- n/a

## Decision

Continue without UAT; the ticket stays done and the PR body says UAT did not run.

## Why

A missing config, a start failure or an agent failure is not an acceptance failure, so no code fix is attempted.

## Consequences

The running app was not checked against the original request.

## How to reverse

Run /harness:uat 545 by hand.
