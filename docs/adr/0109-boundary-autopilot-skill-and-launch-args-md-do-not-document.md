---
ticket: 477
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-10-29
---

# 0109. Boundary: autopilot SKILL and launch-args.md do not document the sandbox argument

## Context

The ticket allows plugins/harness/skills/autopilot/SKILL.md only if it documents the sandbox arg. It does not; the args are listed in plugins/harness/skills/autopilot/references/launch-args.md, which is not in the ticket's file list. The workflows README named in the ticket does not exist; the per-stage worktree text sat in docs/workflows.md (found by grep and changed).

## Options

- Edit launch-args.md to document args.sandbox
- Leave it and report

## Decision

launch-args.md and autopilot SKILL.md are not changed. args.sandbox is optional (default worktree), so autopilot launches keep working.

## Why

A change outside the listed files is not made.

## Consequences

Autopilot cannot yet pass sandbox: clone without the owner editing the launch args by hand.

## How to reverse

Add a sandbox line to launch-args.md.
