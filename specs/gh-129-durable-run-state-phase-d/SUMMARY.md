# gh-129-durable-run-state-phase-d — Summary

Lane: normal
Confidence: high
Reason: Zero risk flags fire (no auth/authz/data-loss/audit/external-system/public-contract/
cross-platform-product-split/existing-behavior-change/weak-proof/multi-domain — this phase
documents and validates already-shipped, already-tested behavior; it does not change it). No
hard gate: no edits to `skills/*/SKILL.md`, `hooks/*`, `.claude/settings.json`, or a core skill
engine. Lane is `normal` rather than `tiny` only because the work spans >1 file and >3 discrete
steps (per `rules/plan-format.md`'s PLAN.md trigger), not because of risk.
Flags: none
Affects: specs/durable-run-state/ (new canonical spec folder), specs/STATE.md (RUN/event
ownership + compatibility boundary documentation), specs/gh-129-durable-run-state-phase-a/b/c
(SUMMARY Verify-row evidence), .github/workflows/harness-ci.yml (already runs a macOS+Ubuntu
matrix — Phase D validates against it, does not need to author a new one)
Input-type: spec slice

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<paste the original request, verbatim>
"yes, let do it"

Context established earlier in the same conversation: the user is working through GitHub issue
#129 ("Durable Run State Contract") phase by phase. Phase A (engine + CLI, PR #164), Phase B
(portable deployment, PR #166), and Phase C (core workflow checkpoints, PR #167, open against the
epic branch) are complete. This request starts Phase D.

Phase D scope, quoted verbatim from GitHub issue #129 ("Phase D — Evidence and rollout"):

- Document RUN/event ownership and the compatibility boundary with `specs/STATE.md`.
- Add a focused `research-brief.md`, `design.md`, and canonical `PLAN.md` under
  `specs/durable-run-state/`.
- Populate SUMMARY Verify rows with re-runnable evidence.
- Validate on macOS and Ubuntu through the existing CI-equivalent suite.

Acceptance criteria, quoted verbatim from the issue:

- A new run can be initialized from a spec SUMMARY and produces valid `RUN.json` + `events.jsonl`.
- Valid transitions update both artifacts consistently.
- Invalid, skipped, reversed, and post-terminal transitions fail without mutation.
- Rebuilding from `events.jsonl` reproduces the current projection.
- Duplicate event replay is idempotent; conflicting event reuse is rejected.
- Concurrent writers produce contiguous event sequences.
- Corrupt or truncated logs fail visibly and do not silently fabricate state.
- Active runs are discoverable from SessionStart/status surfaces.
- Fresh install and resync deploy `.claude/runtime/` and preserve consumer-owned additions.
- Legacy specs remain usable.
- Full harness tests pass on macOS and Ubuntu.

Non-goals, quoted verbatim from the issue: Proposal 2 retry budgets/self-healing/agentic
recovery; Slack/GitHub/Linear/PagerDuty event adapters; automatic merge detection; raw transcript
sync; multi-run archival per slug; SQLite or third-party runtime dependencies; a dashboard or
automatic policy self-modification.

Base branch: `feat/gh-129-durable-run-state` (the epic/integration branch for the whole issue,
not `main`/`loop` directly).

## What changed

<pending — filled in after implementation>

### Rationale

<pending — filled in after implementation>

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

Route: /using-git-worktrees → /subagent-driven-development
