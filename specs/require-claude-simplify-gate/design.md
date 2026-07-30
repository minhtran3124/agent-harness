# Design — Signal-gated Claude Code `/simplify` stage

> Slug: `require-claude-simplify-gate`  
> Date: 2026-07-30  
> Lane: high-risk

## 1. Decision

Add one branch-level Claude Code `/simplify` stage after every task has passed its task review and
before the final branch review package is created. Require it only when a deterministic policy
finds reviewable code scope; keep tiny low-signal and non-code changes advisory or skipped.

Do not create a repository skill named `simplify`. The workflow invokes Claude Code's bundled
skill through its Skill tool and validates the client capability first.

## 2. Pipeline

```text
all tasks green
  → resolve simplify policy
  → clean checkpoint + capture PRE_SIMPLIFY_SHA
  → invoke bundled /simplify once
      ├─ no-op → record evidence
      └─ changed
           → targeted verify
           → combined spec + quality delta review
           → commit accepted cleanup
           → record POST_SIMPLIFY_SHA
  → create branch review package
  → context audit when triggered
  → correctness review
  → intent review
  → write receipt at reviewed HEAD
  → finishing gate / PR
```

The stage lives inside the durable run's existing `verifying` phase. It does not add a new run
state. Resume logic treats a valid simplify receipt entry as idempotent evidence and treats
missing, pending, or stale evidence as a reason to resume the review chain.

## 3. Policy authority

Create `rules/simplify-stage.md` as the human-readable authority and a deterministic helper as the
executable policy. Inputs:

- lane;
- explicit base and HEAD;
- changed paths;
- changed source line count;
- Claude Code version.

Outputs:

- `required: true|false`;
- a bounded reason enum;
- capability status;
- exact target range.

Reviewable source excludes documentation, specs bookkeeping, evaluation results, vendored files,
generated artifacts, and derived `.claude/` output. The policy must operate on the explicit
resolved base rather than guessing the default branch.

## 4. Mutation boundary

Before invocation:

1. all implementation work is committed;
2. the worktree is clean;
3. the resolved base and pre-simplify HEAD are recorded;
4. Claude Code is at least 2.1.154;
5. required skill invocation is available.

The bundled skill runs exactly once. It may not:

- introduce a dependency;
- change a public contract;
- remove requested behavior;
- change auth, migration, transaction/session, or validation architecture;
- edit out-of-scope files without escalation.

These are existing Rule-4 or blast-radius boundaries. Because `/simplify` auto-applies edits, the
controller inspects the resulting delta before accepting it.

If the result is changed:

- run a targeted automated check;
- generate a deterministic package for `PRE_SIMPLIFY_SHA..working/post HEAD`;
- dispatch the combined task reviewer with plan constraints and the simplify delta;
- reject or escalate any `cannot_verify`, Critical, Important, spec failure, or quality failure;
- commit only accepted cleanup;
- generate all final-review evidence after that commit.

A failed cleanup is not repaired speculatively. Revert the isolated cleanup delta or escalate; do
not loop `/simplify`. One invocation is the default budget.

## 5. Receipt extension

Use the existing `.review-receipt.json`:

```json
{
  "type": "simplify",
  "result": "pass",
  "blocking_open": 0,
  "required": true,
  "policy_reason": "non_tiny_source_change",
  "claude_code_version": "2.1.220",
  "base_sha": "<40 hex>",
  "pre_sha": "<40 hex>",
  "post_sha": "<40 hex>",
  "outcome": "changed",
  "changed_files": ["path/to/file"],
  "verify_exit": 0,
  "spec_verdict": "pass",
  "quality_verdict": "approved"
}
```

For `no-op`, `pre_sha == post_sha`, `changed_files` is empty, and delta-review fields may be
omitted. A required stage cannot be represented as `skipped`. Optional/skipped cases are recorded
in SUMMARY with the deterministic policy reason and do not add a passing review entry.

The checker validates:

- resolved full SHAs and ancestry;
- minimum version;
- allowed reason/outcome values;
- changed/no-op field consistency;
- verification and delta-review pass for changed outcomes;
- post-simplify source SHA is covered by the final reviewed HEAD;
- no unreviewed non-specs code follows the receipt.

## 6. Failure behavior

| Failure | Route |
| --- | --- |
| old or missing Claude Code | STOP with upgrade instruction |
| skill unavailable in a required case | STOP; never silently skip |
| dirty worktree before invocation | STOP and identify paths |
| no-op | record and continue |
| changed + tests fail | reject cleanup delta; record failure |
| changed + spec/quality fails | reject or escalate finding |
| Rule-4 boundary crossed | escalate; do not auto-accept |
| final reviewer changes code | re-run affected review and refresh receipt |

## 7. Rollout

### Shadow

Build and run an isolated corpus before hard-gate wiring. Preserve raw transcripts and all rejected
candidate outputs.

### Required

Enable the receipt requirement only if the pinned candidate passes quality and value gates. The
commit-time hook stays warn-only; the finishing gate is the deterministic enforcement point.

### Recalibration

Any future Claude Code release that changes `/simplify` semantics invalidates the pinned eval.
Upgrade the recorded supported version only after rerunning the corpus.

## 8. Alternatives rejected

- **Require for every task:** duplicates per-task quality review and multiplies cost.
- **Require for every branch, including docs-only:** fixed ceremony without meaningful cleanup.
- **Run after final reviews:** creates a stale receipt by design.
- **Create a local `simplify` skill:** risks shadowing the vendor skill and silently changing
  semantics.
- **Use `/code-review --fix`:** overlaps the repository's correctness oracle and no longer matches
  the cleanup-only ownership boundary.
- **Keep warn-only forever:** leaves branch-level cleanup dependent on memory rather than workflow.

## 9. Assessment

This section states the cost side explicitly, since a design that only lists benefits cannot answer
"is this worth doing."

**Cost:**

- **Footprint.** This is a high-risk-lane change: a new policy checker, a sandboxed shadow-eval
  harness, an evidence recorder, receipt/finishing-gate extensions, and SDD prose wiring — not a
  small addition to review.
- **Vendor-version dependency.** The stage is pinned to Claude Code ≥ 2.1.154's bundled `/simplify`
  skill. That is a new dependency on behavior this repository does not control; any future release
  that changes `/simplify`'s semantics invalidates the pinned shadow-eval and must be recalibrated
  (§7 Recalibration) before the version floor can move.
- **Recurring cost.** Every required branch now pays one `/simplify` invocation plus a combined
  spec/quality delta review before it can finish — real per-branch latency and reviewer-agent cost,
  not a one-time setup charge.

**Benefit:** the shadow-eval corpus (`evals/skills/simplify-stage/results/comparison.md`) reached a
Round-3 ACCEPT verdict — all 8/8 fixtures matched `truth.json`, `quality_pass: true`,
`value_pass: true` (`value_score: 4` against a minimum of `3`) — evidence that the bundled skill's
cleanup-only behavior is safe and adds signal beyond what per-task review already catches, for the
signal-gated subset of branches this stage actually requires.

**Verdict:** worth doing for the reviewable-code-change subset this policy actually requires (see
§3 policy authority and the `POLICY_REASONS` bounds in `scripts/check_claude_simplify.py`) — the
recurring cost is paid only when there is reviewable scope, and the recalibration cost is bounded to
version bumps that actually change `/simplify`'s behavior, not every Claude Code release.

## 10. Success definition

The design succeeds when required code-bearing branches cannot finish without a version-valid,
durably recorded simplify stage; any simplify mutation is independently verified before all final
oracles; tiny/non-code work avoids unnecessary ceremony; and the shadow corpus shows no quality
regression.
