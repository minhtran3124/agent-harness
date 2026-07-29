# Design — Adopt the Superpowers 6.0 review-pipeline improvements

> Slug: `superpowers-6-review-pipeline-adoption` · Date: 2026-07-29 · Lane: high-risk

## 1. Problem

The harness still uses the pre-6.0 per-task shape:

```text
implementer → spec reviewer → quality reviewer
```

Both reviewers inspect substantially the same task and diff. The quality reviewer already returns
severity, but SDD blocks on every finding. The spec reviewer has only a binary result. Task text is
pasted into dispatches, diff reconstruction is repeated, and new PLAN files do not carry explicit
global constraints or interface contracts.

The final context/correctness/intent oracles are intentionally independent and are not the target
of reviewer consolidation.

## 2. Target architecture

```text
PLAN
  → deterministic task brief file
  → isolated implementer
  → implementer report file
  → deterministic review package file
  → read-only task reviewer
       spec_verdict: pass | fail | cannot_verify
       quality_verdict: approved | needs_fixes
       findings: Critical | Important | Minor
  → Critical/Important: one fix dispatch, then re-review
  → Minor: durable record, continue
  → final context/correctness/intent chain over a branch review package
```

Bulk artifacts live under a Git-resolved SDD state directory and are passed by path. Exact values
have one source. Isolated prompts receive complete task-local contracts and never rely on parent
history.

## 3. PLAN contract

New markdown plans add:

- `## Global Constraints` for exact cross-task requirements;
- `Criteria` mapping from task to `SC-n`;
- `Interfaces` with exact `Consumes` and `Produces`;
- right-sizing: one task equals one independently testable, meaningfully reviewable unit.

Legacy markdown/XML plans remain executable. New requirements apply only to plans created after
the contract's cut-over date.

## 4. Review semantics

- Spec and quality remain separate verdicts even though one reviewer produces both.
- `cannot_verify` is deny-on-unknown. The controller performs a focused check or supplies missing
  context once; unresolved unknown escalates.
- Critical/Important findings block and are fixed together.
- Minor findings never disappear: they are written to SUMMARY and passed to final review.
- A plan-mandated defect remains a finding and requires a human decision.
- The reviewer cannot be coached to ignore or pre-rate a finding.

## 5. Security and isolation

The task reviewer uses a narrower read-only agent surface. It may inspect the supplied files and
perform explicitly allowed read-only searches. A focused test request is routed through the
test-runner rather than granting general mutation-capable Bash.

The shared diff package does not merge oracle context:

- correctness sees runtime evidence, not PLAN intent;
- intent sees verbatim intent and approved SC evidence, not PLAN prose;
- context propagation keeps its consumer-delivery matrix.

## 6. Evaluation and rollout

Freeze the current dual-review baseline before deleting either prompt. Compare it with the
candidate on the same fixtures, model/client settings, clean worktree, and first-run discipline.

Quality gates precede efficiency gates:

1. no new miss, unsafe pass, false-positive class, or skipped handoff;
2. `cannot_verify` cases remain unknown until resolved;
3. reviewer dispatches fall from two to one per clean task;
4. candidate reviewer token/runtime medians must not be worse than baseline;
5. deterministic tests and the full CI-equivalent suite pass.

Roll out source first, deploy the derived `.claude/` copy only after review, and never merge without
human review.

## 7. Non-goals

- Removing lane routing, hooks, SC coverage, receipts, or escalation rules.
- Merging the three final review oracles.
- A multi-harness portability rewrite.
- Treating upstream's 50–60% result as our target.
- Rewriting historical plans or benchmark results.
- Using the cheapest model for every reviewer.
