---
problem_type: decision
module: scripts/harness-audit
tags: bash-set-u, empty-array-expansion, jsonl-parsing, defensive-parsing, harness-scripts, ci-macos-ubuntu
severity: critical
applicable_when: A future spec or plan says a metric/log/artifact should be recorded "every CI run" (or similarly literal per-run language) and the repo has both a per-push/PR workflow and a separate post-merge/event-sourced workflow — check which one the literal wording actually requires before wiring the write into either, especially when the per-push workflow would need a new write permission it doesn't currently have.
affects:
  - scripts/bookkeeping.sh
  - .github/workflows/post-merge-maintenance.yml
supersedes: null
confidence: high
confirmed_at: 2026-07-04
---

## Applicable When

A future spec or plan says a metric/log/artifact should be recorded "every CI run" (or
similarly literal per-run language) and the repo has both a per-push/PR workflow and a
separate post-merge/event-sourced workflow — check which one the literal wording actually
requires before wiring the write into either, especially when the per-push workflow would need
a new write permission it doesn't currently have.

## Context

The v0.3 spec (`docs/harness-v03-plan-overview.md`, Wave 4) called for emitting a trend JSONL
line to `docs/harness-experimental/audit-log.jsonl` "every CI run," to turn a single-sample
advisory drift finding into a real trend. Two CI workflows exist: `harness-ci.yml` (runs on
every push and PR — the literal "every CI run") and `post-merge-maintenance.yml` (runs once per
merged PR, already used by `scripts/bookkeeping.sh` to write VERSION/CHANGELOG/trust-metrics.md).
A choice was needed about which workflow gets the new append step.

## Options Considered

- Option A: New per-push step in `harness-ci.yml` — literally satisfies "every CI run" but
  requires granting `harness-ci.yml` a new `contents: write` permission it doesn't have today,
  adds a commit-back-to-branch pattern on arbitrary PR branches (not just the default branch),
  and produces much higher write volume/noise (one row per push).
- Option B: Append the trend line inside `scripts/bookkeeping.sh`, which already runs once per
  merged PR via `post-merge-maintenance.yml` — a workflow that already holds `contents: write`
  + `pull-requests: write` and was built in an earlier v0.3 wave specifically as the repo's one
  write-back mechanism. No new workflow, no new permissions, one row per merge instead of per
  push.

## Decision & Rationale

Option B was chosen: the `audit-log.jsonl` append was added as a new step at the end of
`scripts/bookkeeping.sh`, and `post-merge-maintenance.yml`'s existing `git add` list was
extended with `docs/harness-experimental/audit-log.jsonl`. Deciding factors: (1) zero new CI
permission surface — Rule 4 (`auto-correct-scope.md`) treats CI permission/write-back changes
as architectural judgment that must not be auto-applied; (2) reuse of infrastructure already
deliberately built and trusted for this exact purpose (event-sourced write-back on merge) beats
standing up a second one; (3) merge-cadence data is less noisy and still satisfies v0.3's own
success criterion of "≥3 weeks of JSONL data." This narrows the literal "every CI run" spec
wording to "every merge" — a divergence from the literal request that an intent-review pass
flagged (the narrowing rationale lived only in the internal PLAN.md, not anywhere the
original-intent record could see it). The user was asked directly with this exact two-option
framing and explicitly confirmed Option B is correct.

## Consequences

Enables: zero new CI write-permission surface area; trend data reuses an already-trusted,
already-audited write-back path; lower noise (one row per merge, not per push).
Constrains: the trend log accumulates at merge cadence, not push cadence — fewer, more widely
spaced data points per week than a literal "every CI run" reading would produce. If a future
wave wants finer-grained per-push trend data, that requires revisiting this decision and
building the Option-A-style new permission-bearing workflow step; this record exists so that
future work doesn't rediscover the trade-off from scratch or build Option A without knowing
Option B was deliberately chosen instead.
