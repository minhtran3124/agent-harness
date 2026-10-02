---
problem_type: decision
module: harness
tags: review-chain, model-binding, ensemble-diversity, effort, runtime-bindings, opus-5-5, reviewer-independence
severity: standard
applicable_when: Choosing or changing the model/effort pinned to a review role (reviewer, task-reviewer, correctness scorer, intent reviewer), or adding a check that review stages use a different model than the implementer.
affects:
  - agents/runtime-bindings.json
  - scripts/render_runtime_entry.py
  - skills/correctness-review/correctness-scorer-prompt.md
  - skills/intent-review/intent-reviewer-prompt.md
supersedes: null
confidence: high
confirmed_at: 2026-10-02
---
## Applicable When

Choosing or changing the model/effort pinned to a review role, or reintroducing a rule that review
stages must run on a model different from the implementer's.

## Context

Until 2026-10-02 the Claude review roles pinned `claude-opus-5` (`reviewer` at `high`) while
`coding` pinned `claude-opus-5-5`, and `scripts/render_runtime_entry.py` raised when the correctness
scorer shared the finders' model or the intent reviewer shared the implementer's ("ensemble
diversity"). Anthropic's Opus 5.5 guidance reports Opus 5.5 at `medium` effort outperforming Opus 5
at `high` on code review with fewer tokens, and makes effort — not prompt wording — the thinking
control.

## Options Considered

- **Reviewers on `claude-sonnet-5-5`** — keeps diversity; not chosen.
- **Keep diversity by moving `coding` off Opus 5.5** — not chosen.
- **Per-runtime `model_diversity` policy flag** (Claude off, Codex on) — unrequested schema.
- **Downgrade the checks to warnings** — permanent noise on Claude.
- **Drop the rule; reviewer and task-reviewer on `claude-opus-5-5` at `medium`** — chosen by the user.

## Decision & Rationale

The user chose Opus 5.5 at `medium` for both review roles and dropped the diversity rule for every
runtime. Review independence now rests on fresh context per pass, structurally read-only reviewer
bindings, and plan-blindness; the earlier learning `prose-encoded-state-logic-accrues-contradiction-chains.md`
already observed that a different reading frame, not a different model, is what catches the
missed class.

## Consequences

- Claude scorer, finders, intent reviewer and implementer all resolve to `claude-opus-5-5`.
- Codex bindings still differ (`gpt-5.6-terra` vs `gpt-5.6-sol`) by mapping only; nothing enforces
  it, and the Codex reviewer `model_class` still says "distinct".
- `correctness_scorer → coding` in `adapters/runtime-entry-bindings.json` now has no stated
  rationale; the scorer's model follows the implementer's.
- Whether quality held is measured by re-running `evals/skills/review-chain` and
  `evals/skills/task-review` after redeploy (prior baselines used other models, so a difference
  is not attributable to this change alone).

## Related

- docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md
- docs/solutions/harness/prose-encoded-state-logic-accrues-contradiction-chains.md
- specs/opus-5-5-review-bindings/design.md
