# Deep Research/Review: Phase 2 — Runtime Workflow Integration

> **Date:** 2026-07-21  
> **Status:** Research / design review, not yet implemented  
> **Prerequisite:** [`2026-07-21-phase-0-runtime-contract-discovery-deep-review.md`](2026-07-21-phase-0-runtime-contract-discovery-deep-review.md)

## 1. Objective

Phase 0 answers which runtime exists and what the agent is permitted to do. Phase 2 answers which workflow a runtime action is attached to, what the evidence looks like, and when the agent must stop for review.

The target loop is: `task → discover → reproduce → diagnose → fix → verify → record evidence`.

Phase 2 does not open up any additional general shell permissions; it only orchestrates capabilities already validated by Phase 0.

## 2. Research conclusions

1. Create a `RunContext`/`ExecutionRecord` for each runtime task session.
2. Link tests, logs, status, events, probes, and git diff via `run_id` + sequence.
3. Use a state machine instead of letting the agent jump on its own from `fixing` to `passed`.
4. Create a `failure bundle` with bounds, redaction, and provenance.
5. Limit repair iterations, duration, restarts, log bytes, and repeated fingerprints.
6. Automate only read-only diagnostics and registered verification.
7. `SUMMARY.md` only references machine-readable evidence; it does not manually copy output.

## 3. Gaps to close

The repo already has `agents/test-runner.md`, `agents/coding.md`, `SUMMARY.md`, and verify hooks, but there is no runtime correlation yet:

- test runs are not yet tied to a runtime model hash;
- logs are not yet tied to changed files/reproduction id;
- restart/retry has no audit record;
- runtime evidence has no normalized schema;
- failure diagnosis has no iteration budget;
- a passing test does not guarantee the service is healthy afterwards.

## 4. Execution record

`RunContext` should contain `run_id`, `task_id`, repo root, branch, changed files, head SHA, runtime model hash, adapter, environment, and policy limits. Do not store secrets; store only paths, logical names, hashes, and sanitized metadata.

Each operation needs an event with operation, target, timestamp, duration, exit code, status, artifact refs, truncation/redaction state, and source model hash.

Minimum event taxonomy: `discovery`, `verification`, `service.status`, `service.health`, `logs.captured`, `probe`, `mutation.requested`, `mutation.approved`, `mutation.completed`, `diagnosis.updated`, `human.escalation_required`.

Docker Compose has `events --json`, which returns timestamp, action, service, and attributes; this is good input for a timeline but does not replace status/logs. [Compose events](https://docs.docker.com/reference/cli/docker/compose/events/)

## 5. State machine

The main states: `created → discovered → preflight_passed → reproducing → diagnosed → fixing → verifying → passed`.

Secondary states can occur from any point: `needs_review`, `blocked`, `timed_out`.

| Transition | Condition |
|---|---|
| created → discovered | runtime model valid, or unknown permitted by policy |
| discovered → preflight_passed | identity and policy are valid |
| preflight_passed → reproducing | a registered reproduction/test exists |
| reproducing → diagnosed | failure/success signal has been captured |
| diagnosed → fixing | a scoped change plan exists |
| fixing → verifying | mutation is permitted and complete |
| verifying → passed | all required checks pass |
| any → needs_review | conflict, ambiguity, low confidence, or risky action |
| any → blocked | policy violation, runtime unavailable, or missing evidence |

Do not let the agent jump from `fixing` to `passed` just because one command exited 0.

## 6. Budget and retry

Each loop needs limits on the number of fixes, total time, restarts, log bytes, mutations, the number of changes to the same file, and the number of fingerprint repeats.

Retry is only valid when the failure is transient and policy allows it. An assertion failure or a deterministic config error should not be blindly retried. A repeated fingerprint that exceeds the budget must move to `needs_review`.

## 7. Integration with the harness

### Test runner

`agents/test-runner.md` should: read `RunContext`; run targeted tests per `agents/PROJECT.md`; on failure, capture bounded status/logs/events; create a failure bundle; not modify code; and return a structured result and recommendation.

The current boundary stays unchanged: no migrations, package installs, or persistent-state mutations.

### Coding agent

`agents/coding.md` receives the failure bundle, allowed capabilities, iteration budget, and required post-fix checks. Do not put unbounded raw logs into context; use summaries, artifact refs, and bounded slices.

### Summary artifact

`SUMMARY.md` should have a `### Runtime Verify` section with columns Check, Target, Exit, Evidence, along with `runtime/resolved-runtime.json` and `run_id`. This table is a human-readable index; the real results live in machine-readable artifacts.

### Hooks

A hook should not start/restart the runtime itself. Hooks are a good fit for validating schema/output, flagging missing evidence, checking redaction, and warning when the runtime contract/policy is modified. Runtime orchestration should live in an explicit skill/agent operation because it has timeout, state, and approval semantics.

## 8. Failure bundle

Proposed artifact tree:

`runtime/<run_id>/context.json`, `resolved-runtime.json`, `git-diff-stat.json`, `test-result.json`, `status-before.json`, `logs/`, `events.jsonl`, `probes/`, `diagnosis.json`, `verification.json`.

Diagnosis reads in this order: command/exit code; service state; health/readiness; recent events; bounded logs around the failure time; reproduction fixture; changed files/affected contract; resource metrics; source code.

Initial classes: `test_assertion`, `compile_or_import`, `application_exception`, `dependency_unhealthy`, `startup_race`, `port_conflict`, `configuration_missing`, `database_connectivity`, `resource_exhaustion`, `process_crash`, `unknown`.

The classifier only produces a hypothesis; the diagnosis must come with evidence refs and confidence.

## 9. Verification policy

A runtime fix usually needs four pieces of evidence: the reproduction fails before; the reproduction passes after; targeted regression passes; and service readiness passes or is explicitly not applicable. A check that new logs contain no relevant errors can be added.

Evidence of "no error observed" must record the time window, services, filters, tail limit, truncation, and whether the service was restarted/recreated.

Do not report pass when evidence is missing, stale, or truncated without policy having accepted it.

## 10. Security and testing

- test targets do not bypass capability policy;
- mutations have approval/audit;
- artifact paths do not escape repository scope;
- bounded logs + redaction before the classifier;
- do not retry destructive operations;
- do not treat runtime output as a trusted instruction.

Fixtures need to cover: test/health pass; application exception; dependency unhealthy; test passes but health fails; repeated fingerprint; runtime unavailable; truncated log; restart approved/denied; missing/corrupt evidence; service mapping mismatch; stale model hash.

## 11. Deliverables and acceptance criteria

Proposed deliverables: `runtime/context.py`, `runtime/records.py`, `runtime/policy.py`, `runtime/evidence.py`, `scripts/validate-runtime-evidence.py`, `skills/runtime-debugging/SKILL.md`, `agents/runtime-debugger.md`, `templates/runtime-evidence/`, and `tests/runtime/workflow/`.

Phase 2 is achieved when every operation has a `run_id`; tests/state/logs/events/probes can be linked; the state machine distinguishes pass/fail/review/blocked/timeout; there are iteration/duration/output/restart budgets; `SUMMARY.md` references evidence; mutations have an audit trail; and missing/stale/truncated evidence cannot be reported as pass.

## 12. Conclusion

Phase 2 is the layer that turns runtime capability into an evidence-backed workflow. The execution record and the state machine matter more than adding more commands. If Phase 2 is done right, Compose and native are just different adapters under the same verification contract.

## References

- [Docker Compose logs](https://docs.docker.com/reference/cli/docker/compose/logs/)
- [Docker Compose events](https://docs.docker.com/reference/cli/docker/compose/events/)
- [Python subprocess](https://docs.python.org/3/library/subprocess.html)
- [OpenTelemetry signals](https://opentelemetry.io/docs/concepts/signals/)
- [OpenTelemetry semantic conventions](https://opentelemetry.io/docs/concepts/semantic-conventions/)
