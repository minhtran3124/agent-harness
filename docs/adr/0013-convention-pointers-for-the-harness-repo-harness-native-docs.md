---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: claude
date: 2026-07-17
---

# 0013. Convention pointers for the harness repo: harness-native docs, not target-project docs

## Context

During /bootstrap-xia2 update mode, `agents/PROJECT.md` needed convention-source pointers for execution agents. The bootstrap heuristic's default ("first existing of `.claude/rules/architecture.md`, `docs/architecture.md`, ...") would resolve to `.claude/rules/architecture.md`, which exists — but that file (and `.claude/rules/guidelines.md`) describes the TARGET FastAPI projects this harness deploys into (FastAPI layering, repositories, Pydantic, pytest coverage gates), not the harness repo itself (bash hooks + markdown skills). An agent working ON the harness that followed it would be misled — e.g. look for `app/routers/` or apply pytest coverage gates to bash test suites.

## Options

- Option A: Follow the heuristic literally — point `agents/PROJECT.md` at `.claude/rules/architecture.md` + `guidelines.md`. Trade-off: zero judgment required, file demonstrably exists, but the docs describe a different codebase (wrong audience), so agents would be actively misled.
- Option B: Override the heuristic — point at `skills/README.md` (skill inventory + workflow/handoff map, the de facto architecture doc for this repo) + `rules/behavior.md` (declared "single source of truth" for behavior by CLAUDE.md), and add an explicit maintainer note that `.claude/rules/*` describes target projects, not this repo. Trade-off: deviates from the documented heuristic, requires the note to survive future re-runs.

## Decision

Option B, with the maintainer note.

## Why

The convention index exists specifically to prevent agents from being misled; pointing it at docs about a different codebase defeats its purpose regardless of how cleanly the heuristic resolves. The maintainer note is load-bearing: it records the target-project vs. harness-repo distinction so a future bootstrap re-run doesn't "correct" the pointers back to the FastAPI docs.

## Consequences

Enables: execution agents on the harness get accurate architecture (`skills/README.md`) and behavior (`rules/behavior.md`) sources; the maintainer note inoculates against heuristic-driven regression on re-bootstrap. Constrains: the bootstrap heuristic is no longer self-sufficient for this repo — any automated re-run must respect the note, and the note itself must be maintained as docs move.

Applies when: Make this decision when a meta/tooling repo carries docs describing the projects it deploys into, and a detection heuristic would select those docs as the repo's own architecture/style reference.

Status note: **Status (2026-07-17):** the `/bootstrap-xia2` update-mode and `skills/xia2/PROJECT.md` these decisions were made during no longer exist (bootstrap-xia2 retired; xia2 zero-config). Decision 1's concrete premise is also resolved — `rules/architecture.md` + `rules/guidelines.md` are now thin pointers to project-owned `techstacks/`, not FastAPI-describing docs — but the durable rule holds: **don't point harness-working agents at target-project docs**, and record harness-native Deep triggers rather than empty risk categories. Both decisions are preserved as the reasoning behind today's `agents/PROJECT.md` convention pointers.

Related:
- docs/solutions/harness-bootstrap/meta-repo-signal-remapping.md

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness-bootstrap/ before #567 and is in git history.
