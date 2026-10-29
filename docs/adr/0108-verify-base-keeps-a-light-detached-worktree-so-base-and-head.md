---
ticket: 477
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0108. verify-base keeps a light detached worktree, so base and head environments differ

## Context

The owner confirmed that verify-base keeps a light detached worktree from a trimmed newWt. The head run gets .env and the setup commands from the sandbox; the base worktree gets neither, so the base run can fail only because the environment is missing, and the weak-test check then passes too easily. The advisor offered a detached base sandbox as the alternative.

## Options

- Provision a detached base sandbox (runId RUN_ID-base, no --branch)
- Keep the light worktree (owner-confirmed) and tell the base agent to use the head sandbox's .sandbox.env port and DB and to copy or link .env and dependencies from the head sandbox if a step fails only for that reason
- Record only

## Decision

Keep the light worktree. The base prompt now says it has no untracked files, to use the port and DB from the head sandbox's .sandbox.env, and to copy or link .env or dependencies from the head sandbox (uncommitted) and say so in the report.

## Why

The owner-confirmed decision names the light worktree for verify-base; the prompt text reduces but does not remove the environment gap.

## Consequences

A base run can still fail for environment reasons, which would hide a weak test. The owner should decide whether verify-base needs its own base sandbox.

## How to reverse

Provision a base sandbox with stageProvision (runId RUN_ID-base, no --branch, --from integRef) and point stageVerify base mode at it.
