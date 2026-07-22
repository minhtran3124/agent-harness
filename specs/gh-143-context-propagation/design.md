# Design — Close context-propagation review escapes (gh #143)

**Spec source:** https://github.com/minhtran3124/agent-harness/issues/143 (authored by the repo
owner; treated as the approved design). This file condenses it for local reference — the issue
text governs on any conflict.

## Problem

PR #141 passed the full Claude Code review chain, yet the external Codex reviewer found two
real defects post-push:

- **P1** — `implementer-prompt.md` referenced the path-scoped `auto-correct-scope` rule without
  instructing the isolated implementer subagent to Read it (fixed in `d61e155`).
- **P2** — the correctness reviewer carried an inline Rule-4 STOP list with only 5 of 8 cases,
  while its plan-blind context never loaded the authoritative rule (fixed in `1c0f01d`).

Root cause class: **no oracle proves an instruction reaches every isolated execution context
that consumes it** (main session / implementer / reviewer / scorer). Contributing gaps: an
unverified premise in the PLAN propagated through plan-anchored reviews; `risk-corroboration.sh`
excludes Markdown and `skills/` even though skill/prompt Markdown is executable workflow code;
review completion is not pinned to the final HEAD SHA; fixtures don't exercise this defect class.

## Goal

For changes that alter rule loading, prompt dispatch, agent isolation, policy routing, or
review behavior: (1) enumerate all consumers and execution contexts; (2) prove how each context
receives the authoritative instruction; (3) classify workflow-engine changes at the correct
risk level; (4) prevent stale review results from authorizing a newer HEAD; (5) turn escaped
PR findings into regression fixtures.

## Non-goals (from the issue, binding)

- No seventh generic always-on LLM review pass on normal-lane changes.
- No mirroring of the harness into Codex/Cursor/OpenCode.
- No external Codex review requirement for tiny application changes.
- Prose-only docs changes do not become high-risk.
- No duplicating authoritative policy lists into more prompts.

## Acceptance criteria (condensed from the issue)

1. P1/P2 fixtures fail on pre-fix behavior, pass on current behavior; removing a required
   explicit Read from a covered consumer causes a deterministic test failure.
2. A workflow-engine context/routing change cannot stay `Lane: normal` solely because it is
   Markdown.
3. The consumer audit lists every consumer + delivery mechanism; load-bearing
   `assumed/unconfirmed` entries block completion; main-session evidence is not accepted for an
   isolated subagent.
4. Inline policy summaries cannot drift silently from their authoritative source.
5. Review receipts are tied to HEAD; a new commit makes them stale; the finishing workflow
   refuses a stale blocking review state.
6. Benchmark results report both catch rate and false-positive cost, with limitations stated.
7. `bash scripts/run-tests.sh` passes on macOS and Ubuntu.

## Already shipped (before this plan)

Phase 5's threshold-contract half: issue #152 / PR #153 lowered the scorer default threshold to
75 (matching discrete anchors) and added `tests/scripts/scorer-threshold-contract.test.sh`
(consistency + mutation guard). Remaining Phase 5 scope: benchmark recall/false-positives and
the review-escape ledger.
