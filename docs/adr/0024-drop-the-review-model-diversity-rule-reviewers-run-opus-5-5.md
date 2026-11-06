---
ticket: legacy
stage: solutions-migration
status: accepted
confidence: high
decided_by: owner
date: 2026-10-02
---

# 0024. Drop the review model-diversity rule; reviewers run Opus 5.5 at medium

## Context

Until 2026-10-02 the Claude review roles pinned `claude-opus-5` (`reviewer` at `high`) while
`coding` pinned `claude-opus-5-5`, and `scripts/render_runtime_entry.py` (historical) raised when the correctness
scorer shared the finders' model or the intent reviewer shared the implementer's ("ensemble
diversity"). Anthropic's Opus 5.5 guidance reports Opus 5.5 at `medium` effort outperforming Opus 5
at `high` on code review with fewer tokens, and makes effort — not prompt wording — the thinking
control.

## Options

- **Reviewers on `claude-sonnet-5-5`** — keeps diversity; not chosen.
- **Keep diversity by moving `coding` off Opus 5.5** — not chosen.
- **Per-runtime `model_diversity` policy flag** (Claude off, Codex on) — unrequested schema.
- **Downgrade the checks to warnings** — permanent noise on Claude.
- **Drop the rule; reviewer and task-reviewer on `claude-opus-5-5` at `medium`** — chosen by the user.

## Decision

The user chose Opus 5.5 at `medium` for both review roles and dropped the diversity rule for every runtime.

## Why

Review independence now rests on fresh context per pass, structurally read-only reviewer bindings, and plan-blindness; the earlier learning `prose-encoded-state-logic-accrues-contradiction-chains.md` already observed that a different reading frame, not a different model, is what catches the missed class.

## Consequences

- Claude scorer, finders, intent reviewer and implementer all resolve to `claude-opus-5-5`.
- Codex bindings still differ (`gpt-5.6-terra` vs `gpt-5.6-sol`) by mapping only; nothing enforces
  it, and the Codex reviewer `model_class` still says "distinct".
- `correctness_scorer → coding` in `adapters/runtime-entry-bindings.json` now has no stated
  rationale; the scorer's model follows the implementer's.
- Whether quality held is measured by re-running `evals dir: skills/review-chain` (historical) and
  `evals dir: skills/task-review` (historical) after redeploy (prior baselines used other models, so a difference
  is not attributable to this change alone).

Applies when: Choosing or changing the model/effort pinned to a review role, or reintroducing a rule that review stages must run on a model different from the implementer's.

Related:
- docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md
- docs/solutions/harness/prose-encoded-state-logic-accrues-contradiction-chains.md
- specs/opus-5-5-review-bindings/design.md (historical)

## How to reverse

Write a new ADR that supersedes this one. The original note was in docs/solutions/harness/ before #567 and is in git history.
