# Codex Deep Review: Self-Harness and self-improvement directions for `harness-skills`

> **Date:** 2026-07-22  
> **Primary source:** [Self-Harness: Harnesses That Improve Themselves](https://arxiv.org/html/2606.09498v1)  
> **Scope:** compare the paper's method, results and limitations against the contracts, implementation,
> tests, evals, telemetry and research artifacts currently present in the repository.  
> **Method:** read the paper; trace the actual code/docs; run `scripts/harness-audit.sh`,
> `scripts/harness-status.sh` and the CI-equivalent suite `scripts/run-tests.sh`.

## 1. Conclusion

The repository already has a good foundation for Self-Harness: clear contracts, deterministic tests, audit trend,
trust ledger, behavioral evals, and a `/compound` mechanism that turns failures into a guardrail backlog. However,
it is only at the state of a **harness that can partially observe itself**, not yet a **harness that improves itself
based on evidence**.

The biggest gap is:

> The repo currently measures the consistency of artifacts and a few individual skills, but does not yet record
> execution behavior with enough rigor to prove that a harness change makes the whole workflow better.

The paper proposes this loop:

```text
execution traces
    → weakness mining
    → diverse, minimal candidates
    → held-in/held-out regression validation
    → accepted harness lineage
```

The paper reports held-out pass rate rising from 40.5% to 61.9% for MiniMax M2.5, 23.8% to 38.1% for
Qwen3.5-35B-A3B, and 42.9% to 57.1% for GLM-5. More important than the numbers is that each model received
different changes: artifact recovery, retry discipline, tool-loop limits, environment persistence,
and the shift from exploration to implementation. This is not one long generic prompt shared by all.

## 2. What the paper actually contributes

### 2.1. Harness improvement is an empirical state transition

A harness edit is only worth promoting when you can record:

1. the behavior you want to change;
2. the editable surface that was modified;
3. the evidence that led to the hypothesis;
4. the regression result that justifies the promotion.

Model, evaluator, tool set, budget and benchmark protocol are held fixed; only the harness changes.
This design isolates the effect of a harness edit from changes in the model or the environment.

### 2.2. Failures must be reduced to a reusable mechanism

Weakness Mining does not cluster purely by outcome such as `timeout` or `missing artifact`. Each
failure signature separates three components:

```text
terminal verifier cause
    + causal status of the agent behavior
    + reusable agent mechanism
```

Two runs with the same timeout may need two different interventions if one run got stuck in exact-command
retry while the other explored too long without producing an artifact.

### 2.3. Proposals must be diverse across branches, minimal within each branch

Each candidate targets one failure mechanism and one editable surface. The proposal record must state the expected
behavioral effect and the regression risk. Rejected proposals are still stored so the lineage remains auditable.

### 2.4. Promotion must be non-regressive

The paper only accepts a candidate if it improves at least one split and does not degrade the remaining split.
Stochastic evaluations are repeated and aggregate pass counts are used. Multiple compatible candidates
may be merged into the next harness.

## 3. What the repo already has

| Self-Harness component | Present in the repo | Gap |
|---|---|---|
| Verifiable outcomes | Test suite, `### Verify`, CI gates | Outcomes not yet tied to harness/model/run identity |
| Execution traces | Session transcript, SUMMARY, breadcrumbs | No standard trace schema, causal evidence, or tool-event lineage |
| Failure mining | `/compound`, solutions, improvement backlog | Manual, per-session, no failure clustering across many runs |
| Candidate proposals | Guardrail backlog | No candidate ID, parent harness, hypothesis, isolated branch, or rejected archive |
| Regression validation | Two behavioral eval suites | Manual, small, no diagnostic/promotion/final split |
| Promotion | PR and human review | No machine-readable promotion rule for behavioral candidates yet |
| Model-specific harness | Not present | One shared harness; eval records do not fully pin model/runtime profile |
| Harness lineage | Git history, trust ledger | Lineage not represented by candidate and evidence |
| Safety boundary | Hard gates, strict CI, branch isolation | Editable surfaces and the immutable trusted core are not clearly declared |

### 3.1. Good foundations to keep

- `HARNESS.md` separates risk and ambiguity into two independent axes.
- A completion claim requires re-runnable proof, not just prose.
- `skills/compound/SKILL.md` already has a ratchet from a failure track into
  `docs/harness-experimental/improvement-backlog.md`.
- `evals/README.md` prescribes labeled fixtures, blind runs, first-run records, and claim discipline.
- `scripts/bookkeeping.sh` together with the post-merge workflow has turned the trust ledger into an event-sourced record.
- `scripts/harness-audit.sh` already has JSON output and a trend log.
- `docs/research/harness-review-improvements/2026-07-20-production-agent-harness-review.md` already sketched the right premises:
  `RUN.json`, `events.jsonl`, bounded recovery, and run observability.

### 3.2. Behavioral coverage is still narrow

The repo has 14 skill directories, but behavioral evals currently only measure:

- `/feature-intake`;
- `/correctness-review`;
- `/intent-review`.

`evals/skills/review-chain` has five planted-defect fixtures. `evals/workflow/intake-classifier` has
seven classification fixtures. This is a good foundation but not yet enough to claim full-workflow improvement.
The LLM runs are still manual; CI only runs deterministic scorers and contract tests.

### 3.3. The audit currently measures repository drift, not agent behavior

`scripts/harness-audit.sh` measures SUMMARY missing Verify, stale plans, stale solutions, stale backlog,
manifest degradation, and dirty contract surfaces. It does not yet answer:

- which run repeats tool errors;
- which model frequently misses a required artifact;
- recovery success rate;
- the number of human corrections;
- token/tool-call/wall-time regression;
- which harness version actually increases task success.

Therefore `findings=0, band=healthy` only means the governance artifacts are clean according to the six current
checks; it does not mean harness behavior has been proven optimal.

## 4. What the repo should learn and apply

### 4.1. Standardize behavioral traces before building an optimizer

Every run needs a minimal record:

```json
{
  "run_id": "...",
  "task_id": "...",
  "harness_sha": "...",
  "model_id": "...",
  "model_config_hash": "...",
  "evaluator_version": "...",
  "budget": {},
  "outcome": "pass|fail|blocked",
  "tool_events": [],
  "verification_events": [],
  "artifacts": [],
  "failure_signature": null
}
```

We should extend the existing `specs/<slug>/RUN.json` and `specs/<slug>/events.jsonl` proposal from the current
research directly, rather than creating a parallel observability schema. V1 does not yet need an OpenTelemetry
Collector or raw transcript storage.

Traces must be bounded, redact secrets, and store artifact references instead of committing entire conversations.

### 4.2. Use a three-layer failure signature

Suggested schema:

```yaml
verifier_cause: required_artifact_missing
causal_status: agent_deleted_artifact_after_tool_error
agent_mechanism: artifact_recovery_failure
support: 3
representative_run_ids:
  - run-123
  - run-207
evidence_refs:
  - runtime/run-123/events.jsonl
```

The failure fingerprint is used to deduplicate; the failure signature is used to decide which kind of harness
intervention to apply. Do not auto-patch merely because a fingerprint matches.

### 4.3. Turn `/compound` into a consumer of evidence

`/compound` is a good fit for knowledge crystallization but should not be the only source of evidence. Add
a deterministic layer in front of it:

1. ingest failed run records;
2. group exact failure signatures;
3. only create a weakness when support ≥2 or the failure is safety-critical;
4. produce an evidence bundle containing failed and representative passing behaviors;
5. hand the bundle to `/compound` or a proposer model to generate candidates.

Do not automatically run the whole of `/compound` after every task.

### 4.4. Declare editable surfaces and the trusted core

Extend `harness-manifest.json`:

```json
{
  "editable_surfaces": {
    "prompt_guidance": {"risk": "normal"},
    "skill_workflow": {"risk": "high"},
    "retry_policy": {"risk": "high"},
    "tool_middleware": {"risk": "high"}
  },
  "immutable_surfaces": [
    "evaluation_truth",
    "promotion_rules",
    "permissions",
    "secret_scanning",
    "branch_isolation",
    "hard_gate_vocabulary"
  ]
}
```

An agent may propose a PR for editable surfaces but must not modify the evaluator, answer keys, or the
promotion rule within the same candidate. Policy, permissions, hooks and recovery boundaries still require
human review. Self-improvement does not mean self-authorization.

### 4.5. Every proposal must be small and have lineage

Candidate record:

```yaml
candidate_id:
parent_harness_sha:
model_profile:
target_failure_signature:
evidence_run_ids:
edited_surface:
expected_behavior_change:
regression_risks:
diff_path:
evaluation_runs:
decision: proposed|accepted|rejected
```

Each candidate should modify only one mechanism or one surface. Candidates run in their own worktrees.
Rejected candidates must be stored so the proposer does not repeat the same hypothesis with different wording.

If several candidates pass independently, the merged combination must be tested again. `A pass` and `B pass` do not
prove `A+B pass`.

### 4.6. Build an eval pyramid

Three proposed layers:

1. **Component eval:** each skill, router, reviewer and middleware.
2. **Workflow eval:** request → intake → plan → implement → review → verify.
3. **Real-run shadow eval:** real failures/corrections, redacted and frozen.

Prioritize fixtures for the behaviors the paper proved valuable:

- the required artifact is created early and still exists at the end;
- no infinite retry of the exact same command;
- a tool error switches to artifact-focused recovery;
- exploration has a budget and transitions into implementation;
- environment changes are verified through a new shell session;
- the agent does not finalize while the verifier or a sanity check still fails.

### 4.7. Use three splits instead of only held-in/held-out

One limitation of the paper is that the split called held-out is still used repeatedly to decide promotion.
It is therefore effectively a validation set, no longer a final untouched test.

The repo should use:

- `diagnostic`: traces handed to the weakness miner and the proposer;
- `promotion`: returns only aggregate outcomes to the gate;
- `final-shadow`: must not be queried during candidate search, run only at release/milestone time.

If many candidates are tried on the same promotion set, rotation or a sequential-testing budget is needed to
reduce adaptive overfitting.

### 4.8. The promotion gate must be multi-objective

A candidate is accepted only when:

- the deterministic suite has no regression;
- the behavioral target improves;
- safety fixtures stay at 100%;
- artifact completeness does not decrease;
- false positives and human escalations do not exceed thresholds;
- token/tool-call/wall-time stay within budget;
- no permission is added and no validation is weakened;
- the combined candidate has been re-tested;
- there is a clear rollback and a small diff.

For stochastic evals, use paired repeats and confidence intervals or bootstrap. Two attempts as in the
paper should be treated only as an initial signal, not strong enough for high-risk policy changes.

### 4.9. Add model/runtime overlays, do not fork the whole repo

Keep the architecture:

```text
core harness contracts
    + model/runtime profile overlays
    + project-specific rules
```

There is no need to create multiple copies of the skill tree. Pin model/runtime identity in evals and condition
only some guidance/middleware on the profile when there is evidence. Do not build a large portability layer
until a second model or consumer genuinely uses the repo.

### 4.10. Turn human corrections into a training signal

The trust ledger should add typed interventions:

```text
correction | override | rework | approval | false_alarm
```

The record needs to state the source, run ID, candidate ID, corrected behavior, and commit/PR. This is a
weakness-mining source that is more valuable in practice than only looking at test failures.

## 5. Live finding discovered during the review

`scripts/harness-status.sh` is reading the trust ledger columns incorrectly.

The real schema:

```text
Date | Slug | Lane | Affects | Confidence | Flags | Escalated | Outcome | Notes
```

But the script takes:

```text
column 5 → lane
column 7 → confidence
column 9 → hook
```

Because `awk -F'|'` produces an empty field before the first `|`, the correct mapping must account for that offset.
The current output puts `Affects` into `lane`, `Flags` into `conf`, and `Outcome` into `hook`.

The test `tests/scripts/harness-status.test.sh` only asserts that a data row is rendered and that the script does not
abort; it does not assert the semantic mapping of each field. This is a direct example that having telemetry is not
enough: the telemetry's reader/evaluator also needs regression tests for semantic correctness.

## 6. Critiques of the paper to keep in mind when applying it

### 6.1. Held-out is not a final untouched test

The held-out split's outcome is used in every promotion decision. Candidate search can therefore adaptively overfit
to this split even though the raw traces are not exposed to the proposer.

### 6.2. The primary metric is too narrow

Pass rate does not measure cost, latency, tool calls, safety regressions, human intervention, or the additional
complexity added to the harness.

### 6.3. Two repeats is still weak

With 64 tasks and stochastic agent behavior, two attempts do not provide strong statistical confidence
for high-risk changes.

### 6.4. Candidate merges carry interaction risk

Edits that pass individually can still conflict when merged. The final combined harness must be evaluated as
a new candidate.

### 6.5. The benchmark and the evaluator are the trust bottleneck

The paper acknowledges that accepted edits may be benchmark-specific and depend on the quality of the verifier/traces.
Higher-stakes changes need an acceptance gate stronger than pass-rate non-regression.

### 6.6. Cross-model transfer is not demonstrated

The paper demonstrates model-specific adaptation, but does not fully evaluate running a harness optimized for model
A on model B. The repo should not call an overlay universal without a cross-profile matrix.

## 7. Recommended roadmap

### P0 — Fix semantic observability

- Fix the mapping in `scripts/harness-status.sh`.
- Add a contract test that pins `Lane`, `Confidence`, `Outcome` correctly from the real schema.
- Do not parse columns by magic index when the header can be read into a map.

### P1 — Run evidence contract

- Implement a minimal `RUN.json`, `events.jsonl`.
- Pin model, harness SHA, evaluator, budget and environment identity.
- Bounded retention and redaction.

### P2 — Eval registry

- Declare component/workflow evals.
- Diagnostic/promotion/final-shadow splits.
- Metrics, safety invariants and resource budgets.

### P3 — Weakness miner

- Deterministic failure signatures.
- Support/actionability threshold.
- Evidence bundle containing failed and passing exemplars.

### P4 — Candidate runner

- A separate worktree per candidate.
- Bounded diff and declared surface.
- Lineage plus a rejected-candidate archive.

### P5 — Promotion gate

- Multi-objective acceptance.
- Paired repeated runs.
- Combined-candidate re-evaluation.
- Human-reviewed PR, no auto-merge.

### P6 — Model overlays

- Only implement after there is data for at least two model/runtime profiles.
- Separate the universal core from evidence-backed overlays.

## 8. What not to do right now

- Do not auto-merge self-generated harness changes.
- Do not commit raw transcripts.
- Do not let the proposer modify the evaluator or the promotion rule of its own candidate.
- Do not build a dashboard, an OpenTelemetry backend, or a persistent Collector before the trace schema exists.
- Do not increase system prompt length wholesale without a specific failure mechanism.
- Do not use pass rate as the only metric.
- Do not port a Rust/SQLite/database substrate just to imitate a self-evolving platform.
- Do not automatically run the full ceremony for tiny tasks; keep the principle that ceremony scales with risk.

## 9. Verification snapshot

At the time of the review:

- `bash scripts/harness-audit.sh --json` returned `findings: 0`, `band: healthy`;
- `bash scripts/run-tests.sh` finished `ALL GREEN` for the contract suites that ran;
- Python unit tests and some pytest-dependent cases were skipped because the environment has no pytest;
- behavioral evals are still manual-run and are not part of the CI-equivalent suite;
- the worktree already had changed/untracked research artifacts from before the review; this review did not modify or
  delete those artifacts.

## 10. References

- Zhang et al., [Self-Harness: Harnesses That Improve Themselves](https://arxiv.org/html/2606.09498v1), 2026.
- `HARNESS.md`
- `harness-manifest.json`
- `skills/compound/SKILL.md`
- `evals/README.md`
- `evals/skills/review-chain/README.md`
- `evals/workflow/intake-classifier/README.md`
- `scripts/harness-audit.sh`
- `scripts/harness-status.sh`
- `scripts/bookkeeping.sh`
- `docs/harness-experimental/trust-metrics.md`
- `docs/harness-experimental/improvement-backlog.md`
- `docs/research/harness-review-improvements/2026-07-20-production-agent-harness-review.md`
- `docs/research/harness-review-improvements/2026-07-21-phase-2-workflow-integration-deep-review.md`
- `docs/research/harness-review-improvements/2026-07-21-phase-3-native-diagnostics-deep-review.md`
- `docs/research/harness-review-improvements/2026-07-21-phase-4-advanced-observability-deep-review.md`
