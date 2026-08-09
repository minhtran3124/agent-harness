# Research brief — executable resume cursor (#175)

> Date: 2026-08-09 · Scope: GitHub issue #175, PRs #173/#179, and the current
> `simplify` branch at `951fe97`.

## Executive finding

Issue #175 should remain open and be completed as a hardening pass over the already-landed
`runtime/resume_decision.py`. PR #179 moved the 16-state routing table out of prose, but it did not
implement the full cursor reconstruction proposed by the issue or by its own Task 2.1. The current
helper can classify a durable run state; it cannot yet establish which plan tasks are trustworthy,
which checks must be re-run, or whether the branch evidence agrees with the plan ledger.

This is a correctness gap, not only a maintainability opportunity. A fresh session is instructed to
follow the helper's action exactly, so an incomplete `execute-plan` verdict can cause already-shipped
tasks to be dispatched again.

## Evidence reviewed

- [Issue #175](https://github.com/minhtran3124/agent-harness/issues/175) records 6 of the final 8
  PR #173 findings as contradictions introduced by prose fixes, including a chained failure when an
  interrupt returns to a waiting state.
- [PR #173](https://github.com/minhtran3124/agent-harness/pull/173) introduced separate-session
  resume and the original five-source Step -1 protocol.
- [PR #179](https://github.com/minhtran3124/agent-harness/pull/179) added
  `runtime/resume_decision.py`, reduced the skill prompt, and retired the phrase-matching state tests.
- `specs/skill-prompt-refactor/PLAN.md` Task 2.1 required the helper to read `PLAN.md`, `RUN.json`,
  `events.jsonl`, git history, `SUMMARY.md`, and slug-scoped `STATE.md`; return a cursor, required
  transition, recovered wait metadata, checks to re-run, and drift/corruption; and cover wrong-base,
  stale-STATE, shipped-plan, paused-plan, and completed-wait cases.
- The current helper reads only `RUN.json`, `events.jsonl`, and the plan's `status:` line. Its five
  tests all pass, but the exhaustive-state test asserts only that every result belongs to an allowed
  action set, not that each state receives the correct action.

## Reproduced gaps

### 1. Shipped plan falls through to task execution

Fixture: a valid durable run at `implementing` plus `PLAN.md` `status: shipped`.

Observed result:

```json
{"action":"execute-plan","plan_status":"shipped","reason":"resume plan execution","state":"implementing"}
```

The helper reports plan status but never uses it in the decision. The old contract barred plan-task
execution for a shipped plan while explicitly allowing the post-PR repair states `fixing_ci` and
`addressing_review`.

### 2. Waiting-origin metadata cannot be restored

Fixture: `awaiting_ci(waiting_on=ci-run-42) -> blocked(waiting_on=dependency-pr-9)`.

The helper returns `origin_state: awaiting_ci` and the current blocker, but not the original
`waiting_on: ci-run-42`. Returning to a waiting state without that value is rejected by
`run_state.py`; the resume instruction is therefore descriptive but not executable.

### 3. No task cursor or branch reconciliation

The helper does not parse tasks, Status Log completion claims, task commit SHAs, Verify commands,
SUMMARY deviations, or STATE's slug/freshness. It also does not compare claimed commits with
`BASE..HEAD`. Consequently `execute-plan` does not identify completed, pending, or disputed tasks.

### 4. Snapshot race

`resume_decision.py` reads the event log and projection without the shared lock used by
`run_state.py status`. A transition between those reads can produce a false drift/rebuild verdict
on storage that was always consistent.

### 5. Deployment is file-complete but invocation is ambiguous

The installer ships the entire `runtime/` directory to `.claude/runtime/`, so the helper file is in
the payload. The skill invokes `python3 runtime/resume_decision.py`, however, while a default
consumer install owns `.claude/runtime/resume_decision.py` and does not create a root `runtime/`.
An integration fixture must prove the exact command used by a deployed consumer.

### 6. Contract inventory is incomplete

`harness-manifest.json` registers `runtime/run_state.py` as the durable-state contract surface, but
does not register the resume authority or its skill consumer. Contract-impact checks therefore do
not know that changing the decision schema affects `subagent-driven-development`.

## Existing components to reuse

- `runtime/run_state.py`: state sets, legal edges, chain validation, projection fold, and shared
  read lock. The resume helper must derive state vocabulary from this module rather than copy it.
- `skills/visual-planner/render_plan.py`: current semantics for markdown/legacy task extraction,
  Status Log parsing, and completed-task IDs. A small resume parser may be local to the helper, but
  parity fixtures must prevent it from disagreeing with the renderer.
- `scripts/resolve-base-ref.sh`: the current conservative base-resolution policy. The runtime
  helper cannot depend on this path in a default consumer install, so it should accept an explicit
  `--base` and implement/test the same conservative fallback rules when none is supplied.
- `tests/scripts/runtime-sync.test.sh`: proves runtime payload sync/pruning and is the natural place
  to add a deployed-consumer invocation fixture.

## Boundary: mechanics versus judgment

The helper may decide mechanically:

- storage is absent, corrupt, drifted, or consistent;
- a durable state routes to plan execution, repair, review chain, wait, stop, or rebuild;
- a plan is proposed/active/paused/shipped;
- Status Log claims name real task IDs and resolvable commits inside the selected branch range;
- a slug-scoped STATE hint is current or stale;
- which claimed-complete task Verify commands must be re-run;
- which transition and metadata would be required after a human confirms a wait/interrupt ended.

The helper must not decide:

- whether an external blocker or review has actually completed;
- whether a deviation is semantically acceptable;
- whether a Verify command's successful exit proves the implementation is correct;
- whether an ambiguous or conflicting history should be repaired by inventing state.

Those remain session/human judgments. The command stays read-only and reports structured evidence;
it never executes plan Verify commands or writes run-state artifacts.

## Recommendation

Extend the existing helper in three layers: first expose one neutral locked storage snapshot from
`run_state.py`; then implement a versioned cursor/evidence schema and full decision matrix; finally
wire the deployed invocation, manifest contract, and behavior-level integration tests. Do not add a
second resume command and do not restore prose tables as a parallel authority.
