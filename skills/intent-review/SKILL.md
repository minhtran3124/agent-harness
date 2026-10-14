---
name: intent-review
description: Independently review a finished diff against the user's verbatim original request. Use after correctness review to detect missing requested behavior, intent drift, and unapproved excess scope.
allowed-tools: Read, Grep, Glob, Agent, Task, Bash(git diff *), Bash(git log *)
---

# Intent Review

This is the intent oracle, not a runtime-bug hunt or a style review. Run it standalone with a
supplied intent, or in SDD after correctness review and before finishing a branch.

## Establish a blind oracle

1. Read `### Intent` from `specs/<slug>/SUMMARY.md`; it is the verbatim primary oracle. If it has
   an `Intent-source: specs/<slug>/intent.md @ <sha>` line, first run
   `git diff --exit-code <pin> -- specs/<slug>/intent.md` with that SHA as `<pin>`. On non-zero
   (including 128), STOP: report that the intent changed or the pin is unreachable, and ask
   for feature-intake to re-pin the slug. On zero, the oracle is the intent.md text plus the chat
   request in `### Intent`; where the approved intent.md body differs from that request (or its
   own `## Original request`), the body wins.
2. Optionally read design success criteria and PLAN §3 SC rows as secondary checks. If both
   the `SUMMARY` intent and the design intent are missing, STOP: ask the user instead of reconstructing intent.
3. If a secondary check conflicts with verbatim intent, verbatim wins and the conflict is drift.
4. Set `BASE..HEAD`: task start to HEAD in SDD, merge-base to HEAD for a branch, or an explicit
   range. Give the reviewer the oracle, diff, touched files, SC table, and SUMMARY Verify table,
   but never `PLAN.md` prose or `research-brief.md`.

When SDD supplies `REVIEW_PACKAGE_PATH`, the reviewer reads that `BASE..HEAD` package first
instead of rebuilding the diff. The package holds no intent oracle; do not use it to read
PLAN prose or research material. Otherwise, build the explicit range.

Dispatch `intent-reviewer-prompt.md` in a fresh context. Each finding must quote the intent
sentence it evaluates.

## Route findings

- **gap:** a requested outcome is missing, or a promised SC has no mapped passing Verify row. Fix
  if unambiguous and in scope; otherwise escalate.
- **drift:** the implementation differs from requested behavior. Record equivalent drift as
  advisory; route a material behavior change like a gap.
- **excess:** unrequested behavior or public surface. Report only; do not remove shipped
  behavior without human approval.

Before routing any fix, **read `rules/auto-correct-scope.md`**. Write ambiguous gaps and drift,
and intent conflicts, to `ESCALATIONS.md`; write advisory drift, excess, and deferred findings to
`SUMMARY.md` under `### Intent Findings`. Before handoff, fix each finding with a commit SHA or
record it durably; otherwise completion is blocked.

The task reviewer checks the plan; correctness review checks runtime behavior. Keep this oracle
separate and plan-blind: it catches “implemented correctly, but not what was asked.”
