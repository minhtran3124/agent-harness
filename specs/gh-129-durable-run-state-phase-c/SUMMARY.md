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

Wired the durable run-state engine (`runtime/run_state.py`, Phases A+B) into 8 checkpoints across
6 files: `skills/feature-intake/SKILL.md` (init + investigating + planning),
`skills/subagent-driven-development/SKILL.md` (implementing + verifying),
`skills/finishing-a-development-branch/SKILL.md` (ready_to_merge), `hooks/session-knowledge.sh`
(SessionStart active-run summary), `scripts/harness-status.sh` (Active Runs section),
`.github/workflows/post-merge-maintenance.yml` (shipped-on-merge), plus a
`harness-manifest.json` `contracts` entry registering the 6 consumers. Fixed a real FSM gap found
during design review (no direct `queued→implementing` edge) by adding the `investigating→planning`
checkpoint, scoped to normal/high-risk lanes only.

### Rationale

Phases A and B shipped the engine and its portable deployment, but nothing called it —
`runtime/run_state.py` was inert. This phase closes that gap so the workflow's own steps produce
a durable, queryable record of where each spec is in its lifecycle, without ever gating or
blocking the workflow itself (every checkpoint call is unconditionally `|| true`).

### Alternatives considered

- Mapping the `tiny` lane through the FSM too (via a mock/synthetic chain) — considered and
  reversed; see `design.md` §5 and `ESCALATIONS.md` E001. Only normal/high-risk lanes get the full
  chain; `tiny` stops at `investigating`.
- Extending `deploy-harness.sh`/`install-harness.sh` to distribute `scripts/`/`.github/workflows/`
  generally, making checkpoints 7-8 portable — ruled out as scope creep beyond the issue's ask
  (`design.md` §2c).

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| feature-intake init checkpoint | `grep -q "run_state.py init" skills/feature-intake/SKILL.md` | 0 | | SC-1 |
| feature-intake planning checkpoint | `grep -q "route.<lane>" skills/feature-intake/SKILL.md` | 0 | | SC-2 |
| subagent-driven-development implementing checkpoint | `grep -q "plan.execution_started" skills/subagent-driven-development/SKILL.md` | 0 | | SC-3 |
| subagent-driven-development verifying checkpoint | `grep -q "tasks.complete" skills/subagent-driven-development/SKILL.md` | 0 | | SC-4 |
| finishing-a-development-branch ready_to_merge checkpoint | `grep -q "pr.opened" skills/finishing-a-development-branch/SKILL.md` | 0 | | SC-5 |
| session-knowledge.sh test suite | `bash tests/hooks/session-knowledge.test.sh` | 0 | 12 passed (8 existing + 4 new) | SC-6 |
| harness-status.sh test suite | `bash tests/scripts/harness-status.test.sh` | 0 | 19 passed (16 existing + 3 new) | SC-7 |
| post-merge-maintenance.yml shipped checkpoint | `grep -q "Run-state checkpoint" .github/workflows/post-merge-maintenance.yml` | 0 | also validated with `yaml.safe_load()` | SC-8 |
| harness-manifest.json contract | `python3 scripts/check_manifest.py` | 0 | | SC-9 |

`bash scripts/run-tests.sh` (the full repo suite) was run manually after wave 1 and again after
wave 2 — both times ALL GREEN (214 python tests + all shell suites), no regressions. Not included
as a Verify row per `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`: a
whole-suite invocation exceeds the 60s per-row cap this table enforces.

### Rollback

- `git revert <sha>` for each of: `9bd1574`, `27329a1`, `2929839`, `e4a89b6`, `018d208`,
  `5b5c09f`, `8924863` (each task is an independent, atomically-revertible commit).

### Harness-Delta

- none

Escalate: resolved — see `ESCALATIONS.md` E001. Decision (2026-07-24, Minh Tran): proceed with
full Phase C scope as specced in the issue, full high-risk chain
(`/brainstorming` → `/xia2` → `/writing-plans` → `/using-git-worktrees` →
`/subagent-driven-development`), backward-compatibility for existing RUN-less specs as an
explicit tested design constraint.
Route: /brainstorming → /xia2 → /writing-plans → /using-git-worktrees → /subagent-driven-development
