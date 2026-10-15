# sdd-start-without-asking — Summary

Lane: tiny
Confidence: high
Reason: One-paragraph prose change to one skill's handoff; no hard gate. Touches a skill, so the warn-mode workflow-engine signal applies.
Flags: workflow-engine
Affects: skills/writing-plans
Input-type: harness improvement

### Intent

i want to update workflow that stop ask the user when start implement with SDD, for now we only have 1 option right? so let start on this current session? dont ask to confirm again.
how do you think about that?

### Intake notes

- The "two modes" were same-session and `resume <slug>`. Resume is a recovery entry point for a later session, not an up-front choice, so the question had only one real answer.

## What changed

The `writing-plans` handoff now invokes `subagent-driven-development` in the current session without asking the user to choose an execution mode or confirm the start. Escalation triggers in `rules/orchestration.md` still stop the start; `resume <slug>` stays the way a later session continues a run.

### Rationale

The prompt cost a human round-trip on every plan and its answer was always "this session"; the orchestration rule already says high-confidence work proceeds (notify-and-proceed), so the question contradicted it.

### Alternatives considered

- Remove `resume <slug>` mentions entirely — rejected: resume is still needed when a run spans sessions.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| harness test suite | `bash scripts/run-tests.sh` | 0 | | |

### Not auto-verified

- That agents now skip the question in practice — reached traceability; no behavioral eval was run.

### Rollback

- `git revert <sha>`

### Harness-Delta

- fix-direct
