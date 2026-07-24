# Phase C — Core Workflow Checkpoints (design)

Spec for `specs/gh-129-durable-run-state-phase-c/`. Phase C of GitHub issue #129 (Durable Run
State Contract). Builds on the merged Phase A engine (`runtime/run_state.py`, PR #164) and
Phase B portable deployment (PR #166), both on the epic branch `feat/gh-129-durable-run-state`.

## 1. Problem

Phases A and B built a durable run-state engine and shipped it to every consuming repo, but
nothing calls it yet — `grep -rniE "run_state|runtime/run" skills/ hooks/ scripts/harness-status.sh`
returns empty. The engine is inert. Phase C wires it into the actual workflow: intake creates a
run, execution advances it, finishing and merge complete it, and two status surfaces
(SessionStart, `harness-status`) let a human or agent see what's in flight.

## 2. Scope

### 2a. From issue #129, "Phase C — Core workflow checkpoints"

- Feature intake initializes and routes a run.
- Planning/execution records `implementing` and `verifying`.
- Finishing records `ready_to_merge`.
- SessionStart exposes bounded active-run summaries.
- `harness-status` reports active runs.
- Existing workflows without RUN artifacts remain backward compatible.

### 2b. Added during this brainstorm (confirmed with the user)

- **`shipped`-on-merge wiring**: `.github/workflows/post-merge-maintenance.yml` calls
  `run_state.py transition --to shipped` when a PR merges. The issue's Phase C bullets stop at
  `ready_to_merge` (finishing-a-development-branch never merges — a human does), but Phase A's
  own design explicitly deferred "verifying a landed/merged SHA" to "Phase C — git/GitHub
  integration," and nothing else in this repo runs after a merge. Confirmed feasible: the
  workflow already resolves both the slug (`scripts/bookkeeping.sh:57`, from the merged PR's
  changed-file list) and the merge SHA (`github.event.pull_request.merge_commit_sha`) for its
  existing trust-metrics bookkeeping — same resolution, reused.
- **`harness-manifest.json` `contracts` registration** (deferred by Phase B): unblocked by this
  phase, since `check_manifest.py` Check C only rejected an empty `consumers` list — Phase C
  creates the first real consumers (the skills/hooks/workflow below). Included here to close
  that loop rather than leave it dangling a third time.

### 2c. Explicit scope boundary — NOT all of Phase C's wiring is "portable"

`SYNCED_DIRS_RE`/`PAYLOAD` (`scripts/deploy-harness.sh:106,383`, `scripts/install-harness.sh:33`)
only distribute `skills/`, `agents/`, `hooks/`, `rules/`, `templates/`, `runtime/`, plus two
individually-listed scripts. **`scripts/` in general and `.github/workflows/` are never synced
to consuming repos.** Confirmed via direct grep (no `.github` or bare `scripts/` reference in
either distribution script). Consequence:

- Checkpoints 1–6 below (feature-intake ×2, subagent-driven-development ×2,
  finishing-a-development-branch, the SessionStart hook) live in `skills/`/`hooks/` —
  **portable**, shipped to every consumer.
- Checkpoints 7–8 (`harness-status.sh`, `post-merge-maintenance.yml`) are **meta-repo-only
  tooling** — they run in this repo's own operation, not something a consumer receives when
  they install the harness. `harness-status.sh` already reads meta-repo-specific operational
  data (`docs/harness-experimental/trust-metrics.md`, `audit-log.jsonl`) that only exists in
  this repo, reinforcing that it was always a maintainer tool, not a consumer-facing feature.
- This is stated explicitly, not silently discovered later: extending distribution to cover
  `scripts/`/`.github/workflows/` generally is out of scope (Non-goals, §5) — it's scope creep
  beyond what issue #129 asked for, and would mean re-touching `deploy-harness.sh`/
  `install-harness.sh` (already reviewed, working) for a need nobody requested.

## 3. Architecture — 8 checkpoints, all non-fatal

**FSM correction (found during design review):** `runtime/run_state.py`'s `FORWARD_TRANSITIONS`
has no `queued → implementing` edge — the real path is `queued → investigating → planning →
implementing`. The original 7-checkpoint draft would have silently failed checkpoint 2 on every
run (non-fatal-by-design means the failure is swallowed, not surfaced), so no run would ever
leave `queued`. Fixed by adding one checkpoint (`investigating → planning`, in feature-intake's
own routing step) rather than changing the engine's FSM.

**Lane scope:** the full chain (checkpoints 2–8) is wired for **normal/high-risk lanes only** —
those are the lanes that actually call `writing-plans`/`subagent-driven-development`/
`finishing-a-development-branch`. The `tiny` lane (direct edit, no plan, hook-gated proof) never
calls those skills, so its runs simply stop at `investigating` after intake (checkpoint 1) and
never advance further. This needs no special-casing: every later checkpoint is already non-fatal,
so a `ready_to_merge`/`shipped` attempt against a run stuck at `investigating` just fails
validation (exit 2) and no-ops, exactly like any RUN-less workflow. Documented in §5 Non-goals.

| # | Where | Call | When | Lane | Portable? |
|---|---|---|---|---|---|
| 1 | `skills/feature-intake/SKILL.md` Step 6 | `init --slug <slug>` then `transition --to investigating --event intake.classifying` | Unconditionally, every lane — same moment `SUMMARY.md` is written | all | ✅ |
| 2 | `skills/feature-intake/SKILL.md` Step 7 (routing) | `transition --to planning --event route.<lane>` | Only when `Route:` resolves to `normal` or `high-risk` | normal/high-risk | ✅ |
| 3 | `skills/subagent-driven-development/SKILL.md` Step 1 ("mark plan active") | `transition --to implementing --event plan.execution_started` | Once, before wave 1 dispatch | normal/high-risk | ✅ |
| 4 | `skills/subagent-driven-development/SKILL.md` (before the final review chain) | `transition --to verifying --event tasks.complete` | After all tasks pass, before `/correctness-review` | normal/high-risk | ✅ |
| 5 | `skills/finishing-a-development-branch/SKILL.md` Step 3 | `transition --to ready_to_merge --event pr.opened` | After `gh pr create` succeeds, before returning the PR URL | any (no-ops if not in `verifying`) | ✅ |
| 6 | `hooks/session-knowledge.sh` (extended, not a new hook) | `list --active --json` | SessionStart, injected as a second `additionalContext` block | n/a | ✅ |
| 7 | `scripts/harness-status.sh` (new section) | `list --active` | On-demand status report | n/a | ⛔ meta-repo-only |
| 8 | `.github/workflows/post-merge-maintenance.yml` (new step) | `transition --to shipped --event ci.merged --sha $MERGE_SHA` | On PR merge | any (no-ops if not in `ready_to_merge`) | ⛔ meta-repo-only |
| — | `harness-manifest.json` `contracts` | new entry, `consumers` = the 8 files above | Once, after the above land | n/a | n/a (metadata) |

**Scope boundary within the FSM:** only the happy-path states above are wired
(`queued`→`investigating`→`planning`→`implementing`→`verifying`→`ready_to_merge`→`shipped`).
`awaiting_ci`/`fixing_ci`/`awaiting_review`/`addressing_review`/`blocked`/`escalated` are
explicitly NOT wired — they'd need CI-failure detection or human-review-wait signals the issue
doesn't ask for here (§5 Non-goals).

## 4. Design decisions

1. **Extend `hooks/session-knowledge.sh`, don't add a new hook.** It already does exactly this
   job (SessionStart → `additionalContext` JSON injection, never-blocks, silent-when-empty) for
   a different data source (`docs/solutions/`). A second data source in the same file is lower
   blast radius than a new hook, and passes `docs/solutions/harness/automation-readiness.md`'s
   "is this really a distinct standing automation" test cleanly — it isn't; it's the same job.
2. **Every checkpoint call is unconditionally non-fatal**, per `automation-readiness.md`'s
   fail-safe requirement: `|| true`/non-blocking on the *command itself*, never an
   exception-allowlist (the pattern that has already shipped bugs twice in this repo per that
   doc's own citations). This is uniform across all 8 checkpoints — a skill or CI step never
   fails because `run_state.py` failed.
3. **`shipped`-on-merge wiring (#8) handles three specific risks, all resolved to "never fail
   the job":**
   - **Slug-fallback collision**: `bookkeeping.sh`'s `pr-N` fallback (when a merged PR touches
     no `specs/<slug>/SUMMARY.md`) has no `RUN.json`. Guard: check `specs/$slug/RUN.json` exists
     *before* calling `transition` at all; skip cleanly (one log line) if not — no attempt, no
     confusing exit-3 in the Action log.
   - **State-precondition mismatch**: `transition --to shipped` is only valid from
     `ready_to_merge`; a run that never reached that state (or already terminal) makes the
     engine return exit 2. Handled the same way as any other engine rejection: log
     `::warning::`, continue, don't fail the job.
   - **Path selection**: use `runtime/run_state.py` (repo-root source), not any deployed
     `.claude/runtime/` copy — the workflow checks out `main`/`loop` directly, never `.claude/`.
   - **Side effect, disclosed not hidden**: non-fatal-on-any-failure can mask a genuine bug in
     `run_state.py` silently for a while. Mitigation: this data is observability-only and
     `RUN.json` is always rebuildable from `events.jsonl`; a run stuck at `ready_to_merge`
     forever is itself visible via `list --active`/`harness-status` — a stuck run self-reports
     eventually, it doesn't vanish. `::warning::` also creates a visible Actions annotation, not
     total silence.
4. **`harness-manifest.json` registration lists real consumers**: the `contracts` entry's
   `consumers` array names the 8 files in §3 that actually call `runtime/run_state.py` (once
   they exist) — not a placeholder, satisfying `check_manifest.py` Check C for real this time.

## 5. Non-goals

- Wiring `awaiting_ci`/`fixing_ci`/`awaiting_review`/`addressing_review`/`blocked`/`escalated` —
  no CI-failure or human-review-wait signal exists to drive them; out of scope for this phase.
- **Mapping the `tiny` lane past `investigating`.** Confirmed with the user: only normal/
  high-risk lanes get the full checkpoint chain (§3). A `tiny`-lane run stops at `investigating`
  after intake and never advances — no mock/synthetic chain is fired for it, no new call-sites
  are added to its direct-edit workflow. Later non-fatal checkpoints (`ready_to_merge`,
  `shipped`) simply no-op against it, same as any RUN-less workflow.
- Extending `run_state.py list` with the issue's originally-spec'd `--prompt` flag (Phase A
  silently dropped it) — nothing in this phase's design needs it; `--json`/plain-text cover
  both consumers (§3 #6, #7). Add it later if a consumer actually needs prompt-shaped output.
- Extending `deploy-harness.sh`/`install-harness.sh` distribution to cover `scripts/` generally
  or `.github/workflows/` — would make checkpoints #7/#8 portable, but nobody asked for that and
  it re-touches already-reviewed, working scripts for an unrequested need (§2c).
- Cross-OS (Ubuntu) CI validation of the full 3-phase contract (Phase D).
- Retroactively initializing a run for a spec that was never `init`-ed (e.g. hand-authored specs
  that skip `/feature-intake`, or a lane whose checkpoint call failed silently) — checkpoint #8's
  RUN.json-existence guard means such specs simply never get run-state tracking. This is
  intentional (observability, not mandatory), stated explicitly here so it isn't mistaken for a
  bug later.

## 6. Testing boundary

Checkpoints 1–5 are `SKILL.md` prose read by an LLM agent, not executable code — not
mechanically unit-testable the way a script is. Checkpoints 6–8 (the hook extension,
`harness-status.sh`, the workflow step) ARE script-testable and get real test coverage mirroring
existing patterns (`tests/hooks/*.test.sh`, `tests/scripts/*.test.sh`). This asymmetry is
inherent to the skills-as-prompts architecture, not a gap this phase can close.
