---
name: intent-review
description: Independently review a finished diff against the user's verbatim original request. Use after correctness review to detect missing requested behavior, intent drift, and unapproved excess scope.
allowed-tools: Read, Grep, Glob, Agent, Task, Bash(git diff *), Bash(git log *)
---

# Intent Review

This is the intent oracle: it is neither a runtime-bug hunt nor a style review. Run it standalone
with a supplied intent, or after correctness review in SDD before finishing a branch.

## Establish a blind oracle

1. Read `### Intent` from `specs/<slug>/SUMMARY.md`; it is the verbatim primary oracle. If it has
   an `Intent-source: specs/<slug>/intent.md @ <sha>` line, first run
   `git diff --exit-code <pin> -- specs/<slug>/intent.md` with that SHA as `<pin>`. Non-zero
   (including 128): STOP, report that the intent changed or the pin is unreachable, and ask for
   feature-intake to re-pin the slug. Zero: the oracle is the intent.md text plus the chat
   request in `### Intent`; where the approved intent.md body differs from that request (or its
   own `## Original request`), the body wins — the user approved it.
2. Optionally read design success criteria and PLAN §3 SC rows only as secondary checks. A missing
   `SUMMARY` intent and design intent is a STOP: ask the user instead of reconstructing intent.
3. If a secondary oracle conflicts with verbatim intent, verbatim wins and the conflict is drift.
4. Determine `BASE..HEAD` (task-start to HEAD in SDD, merge-base to HEAD for a branch, or an
   explicit range). Give the reviewer the oracle, diff, touched files, SC table, and SUMMARY
   Verify table—but never `PLAN.md` prose or `research-brief.md`.

When SDD supplies `REVIEW_PACKAGE_PATH`, the reviewer reads that mechanical `BASE..HEAD` package
first instead of rebuilding the same diff. The package carries no intent oracle; do not use it to
read PLAN prose or research material. Standalone calls without a package retain explicit-range
construction.

Dispatch `intent-reviewer-prompt.md` in fresh context. Every finding must quote the intent sentence it evaluates.

## Route findings

- **gap:** a requested outcome—or a promised SC with no mapped passing Verify row—is missing.
  Fix if unambiguous and in scope; otherwise escalate.
- **drift:** implementation differs from requested behavior. Record equivalent drift as advisory;
  route material behavior changes like gaps.
- **excess:** unrequested behavior or public surface. Report only: do not remove shipped behavior
  without human approval.

Before any fix routing, **read `rules/auto-correct-scope.md`**. Put ambiguous gaps/drift
and intent conflicts in `ESCALATIONS.md`; put advisory drift, excess, and deferred findings in
`SUMMARY.md` under `### Intent Findings`. A finding must be fixed with its commit SHA or durably
recorded before handoff; otherwise completion is blocked.

The plan/spec reviewer is plan-oriented and correctness-review is runtime-oriented. Keep this
oracle separate and plan-blind; it is the check for “implemented correctly, but not what was asked.”
