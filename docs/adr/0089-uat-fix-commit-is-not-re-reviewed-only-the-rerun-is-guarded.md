---
ticket: run
stage: review-fix
status: accepted
needs_review: false
confidence: medium
decided_by: claude (ship workflow: review-fix)
date: 2026-10-29
---

# 0089. UAT fix commit is not re-reviewed (only the rerun is guarded)

## Context

Finding F3 has two parts: the UAT fix lands after code and intent review without re-review, and the rerun starts even when the fix was skipped or failed.

## Options

- Guard the rerun on fix_status fixed only
- Add a re-review stage after the UAT fix

## Decision

Guard the rerun on fix_status fixed only. The PR body already says 'one fix round ran, not re-reviewed'.

## Why

A re-review stage is a new workflow stage and is beyond a safe minimal fix. The guard removes the wasted rerun and the misleading result.

## Consequences

A UAT fix commit still lands unreviewed when it succeeds, and the PR body flags it for the owner.

## How to reverse

Revert commit 26b9f7a.
