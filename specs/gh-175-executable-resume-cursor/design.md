# Executable resume cursor (#175) — Design

## 1. Context and problem statement

`runtime/resume_decision.py` is already the named authority for separate-session resume, but today
it answers only one part of the question: how the current durable FSM state routes. A safe resume
needs two independent results:

1. **Lifecycle route** — execute plan tasks, resume a post-PR repair, resume the final review chain,
   wait, stop, or rebuild.
2. **Task cursor** — which task completion claims are supported by the plan ledger and branch,
   which checks must be re-run, which task is next, and whether session-level blocker/deviation
   evidence changes what may be dispatched.

The skill currently treats the first as if it implied the second. That is the gap this design
closes.

## 2. Goals

- Make one read-only command return a deterministic, versioned resume decision and evidence bundle.
- Cover every state and storage combination behaviorally, without tests reading prose.
- Reconstruct canonical markdown and legacy XML plan task cursors from Status Log completion claims.
- Reconcile claimed task commits with a validated `BASE..HEAD` range.
- Preserve the shipped-plan repair exception and make interrupt recovery executable.
- Consume slug-scoped, non-stale STATE hints and SUMMARY deviations without promoting either into a
  stronger source of truth than it is.
- Work from both this source repository and a default deployed consumer installation.
- Register the helper/schema as a contract surface with explicit consumers.

## 3. Non-goals

- Automatically deciding that an external wait or blocker is resolved.
- Running arbitrary task Verify commands inside the decision helper.
- Mutating `RUN.json`, `events.jsonl`, PLAN, SUMMARY, or STATE.
- Replacing `run_state.py`, changing the 16-state FSM, or adding new lifecycle states.
- Generalizing every PLAN parser in the repository in the same change.
- Inferring task completion solely from changed files or commit-message prose.
- Repairing contradictory evidence by choosing whichever source is most convenient.

## 4. Options considered

### Option A — Keep the PR #179 helper unchanged

Smallest scope, but leaves the reproduced shipped-plan and waiting-origin failures and does not
answer which tasks a new session may dispatch. Rejected.

### Option B — Add `scripts/resume_cursor.py` beside `runtime/resume_decision.py`

Matches the illustrative name in #175, but creates two public callables with overlapping state
logic and an immediate drift problem. It also complicates deployment and skill routing. Rejected.

### Option C — Expand `runtime/resume_decision.py` into the full authority (**chosen**)

Keeps the public entry point already shipped by PR #179, preserves progressive disclosure, and lets
the executable state matrix grow into the evidence/cursor contract without another dispatch layer.

### Option D — Put blocker resolution and Verify execution into the helper

Would make one command superficially complete, but crosses the mechanics/judgment boundary and
runs plan-authored shell commands from a read-only inspection path. Rejected.

## 5. Chosen architecture

### 5.1 Locked durable-state snapshot

Add a public snapshot function in `runtime/run_state.py`, implemented under
`locked_run_readonly`. It returns neutral storage topology plus validated data without printing or
mutating any canonical evidence:

- `untracked`: neither canonical artifact exists;
- `projection-only`: projection exists without the canonical log;
- `events-only`: a valid log exists without its projection;
- `drift`: both exist but the projection differs from a validated fold;
- `invalid`: unreadable storage or an illegal event chain;
- `consistent`: validated events plus their matching projection.

`cmd_status` and `resume_decision` consume the same primitive but retain their distinct policies.
For backward compatibility, status may still print a projection-only store; resume maps it to
`stop` because it cannot trust a projection with no canonical log. Resume maps events-only/drift to
`rebuild`. This removes the current race without silently changing the status CLI contract.

### 5.2 Versioned output schema

Successful CLI invocation prints one JSON object with `schema_version: 1` and stable top-level
keys:

```json
{
  "schema_version": 1,
  "slug": "example",
  "action": "execute-plan",
  "reason_code": "active-plan",
  "reason": "resume remaining plan tasks after verification",
  "run": {"status": "consistent", "state": "implementing"},
  "plan": {"status": "active", "format": "markdown"},
  "cursor": {
    "task_ids": ["1.1", "1.2"],
    "claimed_complete": ["1.1"],
    "pending": ["1.2"],
    "next_task": "1.2",
    "checks_to_rerun": [{"task_id": "1.1", "command": "..."}]
  },
  "git": {"base_ref": "github/simplify", "range": "<sha>..HEAD", "conflicts": []},
  "interrupt": null,
  "session_hint": null,
  "deviations": [],
  "required_transition": null,
  "warnings": []
}
```

Keys remain present with empty/null values where applicable so callers do not infer schema from the
chosen action. `reason_code` is machine-stable; `reason` is human-facing. Known decisions, including
`wait`, `stop`, and `rebuild`, are valid outputs and exit 0. CLI misuse exits 2; an unexpected
internal failure exits 3 after emitting no partial JSON. The skill branches on `action`, not on
English or process status.

### 5.3 Evidence model and precedence

The helper reads six artifacts, each with an explicit strength:

| Source | Mechanical fact supplied | Authority boundary |
| --- | --- | --- |
| `events.jsonl` | legal lifecycle history and interrupt origin | canonical run history |
| `RUN.json` | current projection | trusted only when equal to a locked fold of the log |
| `PLAN.md` | task definitions, Verify commands, status, completion claims | claims, not proof of execution |
| git `BASE..HEAD` | commits actually present on the branch | proves commit presence, not task correctness |
| `SUMMARY.md` | recorded deviations | advisory context; malformed/missing section becomes a warning |
| `specs/STATE.md` | most recent session hint/blocker | consumed only for the same slug and age <=7 days |

Contradictions fail closed. Unknown task IDs, unresolvable claimed SHAs, claimed SHAs outside the
selected range, or duplicate/incompatible plan tasks produce `action: stop` with structured
conflicts. STATE remains advisory and cannot override the durable route. Absence is represented as
unknown; it is never silently converted into completion.

### 5.4 Plan and Status Log parsing

The cursor parser supports both formats already accepted by execution:

- canonical markdown `### Task` sections with `Files/Action/Verify/Done` fields;
- legacy XML task blocks.

Completion IDs come only from Status Log entries that contain a completion marker and real task IDs.
Claimed commits are extracted from the same entry. A parity fixture runs the cursor parser and
`render_plan.py` over representative markdown/XML/status-log inputs and requires the same ordered
task IDs and done set. This bounds duplication without coupling runtime decisions to the visual
renderer at import time.

The helper never reports a claimed-complete task as freshly verified. Instead it returns that
task's exact Verify command in `checks_to_rerun`. The skill must run those commands successfully
before dispatching `next_task`; a failure routes to the existing repair/escalation behavior.

### 5.5 Git base selection

`--base <ref>` is authoritative when supplied and must resolve to an ancestor of HEAD. Without it,
the helper applies the same conservative policy as `scripts/resolve-base-ref.sh`: use the PR base
environment when available, ignore an upstream that points to the current branch itself, otherwise
choose the nearest ancestor ref while excluding current-branch local/remote copies. The output
records both the selected ref and selection reason.

If no base can be derived, candidates are ambiguous, or any completion claim cannot be placed in
the selected range, return `stop`/`base-unresolved` or `stop`/`git-evidence-conflict`. Never guess a
well-known branch name.

### 5.6 Lifecycle matrix

Decision precedence is deterministic: storage invalidity/rebuild first; then terminal, wait,
repair, or review-chain lifecycle routes; then plan validity/status; then task/git evidence; finally
plan execution. Cursor conflicts cannot accidentally route a terminal run into execution, and a
missing task base cannot block a named post-PR repair loop that does not consume plan tasks.

The executable matrix retains these rules:

- `cancelled`, `superseded`, `shipped` run states: `stop`, human decision.
- `awaiting_confirmation`, `awaiting_ci`, `awaiting_review`, `ready_to_merge`: `wait`.
- `blocked`, `escalated`: `wait`, with origin state, current blocker, resume event, and a fully
  specified `required_transition` for use only after the condition is confirmed.
- `fixing_ci`, `addressing_review`: `resume-repair`, including when PLAN status is `shipped`.
- `verifying`: `resume-review-chain`; never sweep task waves again.
- `queued`, `investigating`: `execute-plan` plus the legal catch-up path to `implementing`.
- other active execution states: `execute-plan` only when PLAN is not shipped and evidence is
  consistent.
- PLAN status `shipped`: blocks plan-task execution but does not block the two repair states.
- Missing/unparseable PLAN or an unknown plan status: `stop`; there is no executable task contract.
- An untracked run plus a valid non-shipped plan may execute from the reconstructed task cursor; it
  remains honestly untracked and is never initialized by resume.
- PLAN status `proposed` or `paused`: an execution route includes the required plan activation
  action; it does not silently edit the plan.

For an interrupt whose origin is a waiting state, recover `waiting_on` from the latest earlier event
that entered that origin. Also return the set of legal successors available after that wait
completes; external outcome determines which successor is correct. The helper describes the
transitions but does not assert their external conditions are satisfied.

### 5.7 Session hint and deviations

`STATE.md` is a global, weak source. Parse only the `## Active Spec` block. Include it as
`session_hint` only when `Slug` matches and `Updated` is no more than seven days old; otherwise emit
`state-wrong-slug` or `state-stale` as a warning and ignore its contents for routing. Because the
current STATE shape has no typed blocker field, free-form `Last action` is context for the session,
never an automatic lifecycle override.

Extract `SUMMARY.md ### Deviations` as verbatim bullet records. They inform the resumed session but
do not change lifecycle action mechanically.

### 5.8 Portable invocation and contract registration

Keep source-repository execution at `runtime/resume_decision.py`. Update the skill's command to
resolve the source path first and fall back to `.claude/runtime/resume_decision.py`, the location a
default deploy actually owns. Add a disposable-consumer test that deploys the harness and executes
the exact fallback command successfully.

Register a `resume-cursor-decision` contract in `harness-manifest.json` with surfaces
`runtime/resume_decision.py` and the locked snapshot API in `runtime/run_state.py`; consumers are the
SDD skill/reference and their integration tests. Runtime remains shipped as the existing directory
payload; no second installer entry is needed.

## 6. Safety and observability

- The decision path executes no plan-authored command and never rewrites canonical evidence. The
  engine's existing ignored lock-file mechanism may be acquired/created for a consistent read.
- Tests snapshot canonical file bytes before/after every action family to prove semantic read-only
  behavior, including the `rebuild` verdict.
- Every stop/wait/rebuild reason has a stable `reason_code` and structured conflicting evidence.
- No test reads `SKILL.md` to prove the state matrix. Prose tests are replaced by behavior tests;
  one small integration test may assert the public invocation is wired, not its wording.
- A future FSM state makes the exhaustive action matrix fail until assigned an exact expected
  action.

## 7. Rollout and rollback

Land the snapshot primitive, cursor authority, and wiring in ordered waves. Run focused tests after
each wave and the full CI-equivalent suite before shipping. Deploy into a disposable consumer and
run the exact skill command before merge.

Rollback is one `git revert <implementation-sha>`. The helper is read-only and introduces no data
migration; reverting restores PR #179 behavior. Do not remove or rewrite existing run logs during
rollback.
