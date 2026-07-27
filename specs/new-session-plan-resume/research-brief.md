# Research Brief — bringing back "execute a plan from a new session"

> Slug: `new-session-plan-resume` · Date: 2026-07-26 · Lane: high-risk
> Question: the user wants the retired `executing-plans` skill back, specifically for its
> **run-in-a-new-session** support, without breaking the current workflow. What exists on disk
> today, what was actually lost, and what is the lightest credible path?

## 1. What happened to `executing-plans` (ground truth)

Deleted **2026-07-23** in commit `2995759` ("refactor(skills): waves 2-3 — retire executing-plans,
review-diff, create-pr"), item 4 of `specs/slim-skill-surface`. It was **folded**, not dropped:

| Content of the old skill | Where it lives now |
|---|---|
| Step-0 four-guardrail plan gate | `skills/subagent-driven-development/SKILL.md:23-46` |
| Batch + checkpoint execution in a separate session | `skills/subagent-driven-development/SKILL.md:295-310` (`## Parallel session`) |
| Branch isolation before task 1 | `SKILL.md:50-54` |
| `status: proposed → active` before wave 1 | `SKILL.md:56-61` |
| Final `/correctness-review` → `/intent-review` → finishing chain | `SKILL.md:93-97`, and it now also writes the review receipt (`SKILL.md:215-247`) |

Stated rationale (`specs/slim-skill-surface/design.md:63-67`): *"A skill whose only distinguishing
feature is where it is invoked is not a skill."* Both paths validate the plan, branch, execute
tasks, run both review oracles, and hand off to `finishing-a-development-branch`.

## 2. Constraint: the retirement is mechanically pinned

`scripts/check_slim_surface.py:20` hard-codes `RETIRED = ("executing-plans", "review-diff",
"create-pr")` and fails if any of them returns **to disk OR to `harness-manifest.json` skills[]**.
It runs in `scripts/run-tests.sh` and CI. Restoring the file therefore requires un-pinning the
guard + its test, and `harness-manifest.json` `skills[]` going 12 → 13 (currently 12, verified).
That edit is itself a `workflow-engine` change → high-risk → triggers `/context-propagation-audit`.

Evidence that a second copy drifts: the old `/executing-plans` path **never wrote**
`specs/<slug>/.review-receipt.json`, so `finishing-a-development-branch` Gate 0
(`scripts/check_review_receipt.py`) blocked the push until it was hand-written (recorded in local
memory `executing-plans-needs-manual-review-receipt`). Only the folded path writes the receipt.

## 3. What the fold actually left broken — four delivery gaps

1. **The mode is unroutable.** `skills/subagent-driven-development/SKILL.md:3` reads
   `description: Use when executing implementation plans with independent tasks in the current
   session`. That single line is all the router sees; the parallel-session mode is at **line 295**,
   readable only *after* the skill has been invoked. By this repo's own standard
   (`/context-propagation-audit`), delivery to the `new session` execution context is `assumed` → FAIL.
2. **No resume-cursor protocol.** `## Parallel session` teaches "batch + checkpoint" but never
   answers *"which tasks are already done?"* for a session with no history. The sources all exist
   and no prompt points at them: `## Status Log` in `PLAN.md`, the derived `### Progress` checklist
   (`render_plan.py:777`, ids from `_done_task_ids` at `render_plan.py:582-595`),
   `runtime/run_state.py status --slug`, `specs/STATE.md`, and `git log` on the branch.
3. **`## Status Log` records shas, not task ids.** `rules/wave-parallelism.md:44` says *"Append task
   commit shas"*. `_done_task_ids` extracts `\bP?\d+(?:\.\d+)+\b` **task ids** from entries whose
   text classifies as `kind == "build"` or contains `✓` / "complete". Sha-only entries yield zero
   ids, so the Progress checklist stays empty — the machine-readable cursor exists but is starved of
   input. (Confirmed on a real plan: `specs/harness-reliability-improvements/PLAN.md:290` logs *"All
   9 tasks executed"* — no ids.)
4. **The durable run-state has never run.** `ls specs/*/RUN.json` → **empty** across ~60 specs. The
   FSM (`runtime/run_state.py:160-192`) has `blocked`/`escalated` interrupt states with
   `--resume-event`, plus `list --active` surfaced at SessionStart
   (`hooks/session-knowledge.sh:81-96`). But `init` is only called by `feature-intake:155`; every
   downstream `transition` is guarded `|| true`, so on a spec with no `RUN.json` each checkpoint is
   a swallowed exit-3 no-op. Resume infrastructure with zero exercised paths.

## 4. Adjacent blocker (orthogonal to naming)

A new session opened in a worktree that has no deployed `.claude/` cannot resolve
`/subagent-driven-development` at all — the Skill tool has nothing to load (local memory
`worktree-without-claude-breaks-skill-tool`). `skills/using-git-worktrees` already keeps
`deploy-harness.sh --target` for exactly this reason; the resume section should name it.

## 5. Options weighed

| Option | Cost | Verdict |
|---|---|---|
| Full restore of `skills/executing-plans/SKILL.md` | un-pin guard + test, manifest 12→13, second copy of Step-0 gate + ship gate | **Rejected** — reproduces the drift that caused the receipt gap |
| Thin ~25-line wrapper under the old name | still needs the guard un-pin + a manifest entry, for a pure alias | Rejected by the user |
| **Enhance in place** (chosen) | 3 files, additive, guard untouched | **Chosen** — closes all four gaps at one source of truth |
| Discoverability-only (frontmatter + section order) | 1 file, ~5 lines | Insufficient — leaves gaps 2–4 |

## 6. Verification surfaces that must stay green

`scripts/check_slim_surface.py` (guard untouched), `scripts/check_manifest.py` (skills[] stays 12),
`scripts/lint-doc-truth.sh` (every path named in `CLAUDE.md` / `skills/README.md` / `rules/*.md`
must exist), and `scripts/check_verify_rows.py` / `verify_summary.py` for this spec's own bookkeeping.
