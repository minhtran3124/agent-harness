# gh-129-durable-run-state-phase-c — Summary

Lane: high-risk
Confidence: high
Reason: Two mechanical hard gates fire per `harness-manifest.json`: (1) `high-blast` (block-mode) — Phase C's "SessionStart exposes bounded active-run summaries" bullet requires touching a SessionStart hook, which is `hooks/*`; (2) `workflow-engine` (warn-mode) — "Feature intake initializes and routes a run", "Planning/execution records implementing and verifying", and "Finishing records ready_to_merge" all require editing `skills/feature-intake/SKILL.md`, `skills/writing-plans/SKILL.md` and/or `skills/subagent-driven-development/SKILL.md`, and `skills/finishing-a-development-branch/SKILL.md` — workflow-as-code, not prose. Beyond the mechanical gates, this phase also trips the judgment-only escalation trigger "the change would redefine ... the workflow itself" (`rules/orchestration.md`) — it changes what every downstream skill invocation does at each checkpoint, for every future spec in this repo, not just this one. Confidence is high (the issue's four Phase C bullets are individually clear), but a hard gate + system-redefinition both force escalation regardless of confidence — see Escalate below.
Flags: existing-behavior, weak-proof, multi-domain, public-contracts
Affects: skills/feature-intake/SKILL.md, skills/writing-plans/SKILL.md, skills/subagent-driven-development/SKILL.md, skills/finishing-a-development-branch/SKILL.md, a SessionStart hook, scripts/harness-status.sh — the core workflow-engine surface of this harness
Input-type: spec slice

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<paste the original request, verbatim>
"back to branch feat/gh-129-durable-run-state
and start /feature-intake for phase C"

Context established earlier in the same conversation: the user is working through GitHub issue
#129 ("Durable Run State Contract") phase by phase. Phase A (engine + CLI, PR #164) and Phase B
(portable deployment, PR #166) are both merged into the epic/integration branch
`feat/gh-129-durable-run-state`. This request starts Phase C.

Phase C scope (from issue #129, "Phase C — Core workflow checkpoints"):
- Feature intake initializes and routes a run.
- Planning/execution records `implementing` and `verifying`.
- Finishing records `ready_to_merge`.
- SessionStart exposes bounded active-run summaries.
- `harness-status` reports active runs.
- Existing workflows without RUN artifacts remain backward compatible.

Explicitly out of scope for this phase (deferred per the issue): Phase D (docs rollout,
`design.md`/`research-brief.md`/canonical `PLAN.md` under `specs/durable-run-state/`, cross-OS
CI validation of the full multi-phase contract).

## What changed

<blocked pending escalation — see ESCALATIONS.md>

### Rationale

<blocked pending escalation>

### Alternatives considered

- none yet

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |

### Rollback

- `git revert <sha>`

### Harness-Delta

- none

Escalate: resolved — see `ESCALATIONS.md` E001. Decision (2026-07-24, Minh Tran): proceed with
full Phase C scope as specced in the issue, full high-risk chain
(`/brainstorming` → `/xia2` → `/writing-plans` → `/using-git-worktrees` →
`/subagent-driven-development`), backward-compatibility for existing RUN-less specs as an
explicit tested design constraint.
Route: /brainstorming → /xia2 → /writing-plans → /using-git-worktrees → /subagent-driven-development
