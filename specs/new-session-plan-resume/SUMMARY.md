# new-session-plan-resume — Summary

Lane: high-risk
Confidence: high
Reason: Hard gate `workflow-engine` fires — the diff edits `skills/subagent-driven-development/SKILL.md` and `rules/wave-parallelism.md`, which are workflow-as-code (warn-mode at commit time, still high-risk at intake); only 2 of 10 risk flags fired on their own.
Flags: existing behavior, weak proof
Affects: workflow-engine (skills/subagent-driven-development/SKILL.md, rules/wave-parallelism.md) — plan-execution routing + resume contract
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> review lại workflow hiện tại, tôi muốn mang trở lại skill "executing-plans". ko lam breaking với workflow hiện tại
> nó support việc run ở new session. Hãy research và đưa ra ý kiến

Then, after research was presented, the user chose the "Enhance in place" fork over resurrecting
the skill file, scoped as:

> Enhance in place (Recommended) — 4 thay đổi additive trong subagent-driven-development +
> rules/wave-parallelism: sửa description, thêm Step -1 resume reconstruction, args
> `resume <slug>`, wire task-ids vào Status Log + run_state init. Không đụng check_slim_surface,
> không có file skill mới, zero drift risk.

## What changed

Restores the retired `executing-plans` **capability** — executing/resuming a plan from a new
session — as a first-class, routable mode inside `subagent-driven-development`, instead of
restoring the deleted skill file. Four additive edits across five files:

1. `skills/subagent-driven-development/SKILL.md` frontmatter `description` now names both modes, so
   a new session can route to it without opening the file (it previously said "in the current
   session", making the mode invisible to the router).
2. `## Parallel session` (formerly the last section, line 295) → `## New-session / resume mode`,
   promoted to directly after `## When to Use`, with the worktree `deploy-harness.sh --target`
   prerequisite added and every original sentence preserved.
3. New `### Step -1 — Reconstruct the cursor (resume only)`: read the four cursor sources
   (`## Status Log` + derived `### Progress`, `run_state.py status`, `git log <base>..HEAD`,
   `SUMMARY.md ### Deviations`), **re-run the `Verify` of every task claimed complete**, report
   done/next/blocked, continue from the first task not verified green. Plus
   `run_state.py init --slug <slug> || true` before the `implementing` transition, so a run that was
   never initialized stops silently swallowing exit 3.
4. `rules/wave-parallelism.md` collection protocol now requires **task ids + shas + a completion
   marker** in one Status Log entry (with the entry shape and the reason: `_done_task_ids` derives
   the cursor from ids, not shas). `skills/README.md`, `CLAUDE.md`, and
   `skills/writing-plans/SKILL.md` re-worded to the new mode name.

No skill file created, `scripts/check_slim_surface.py` untouched, `harness-manifest.json` skills[]
still 12. Every review gate, the Step-0 four-check gate, the receipt contract, and the ship gate are
byte-identical.

### Rationale

The retirement argument still holds (`specs/slim-skill-surface/design.md:63-67`: a skill whose only
distinguishing feature is *where it is invoked* is not a skill), and `scripts/check_slim_surface.py`
pins it from returning to disk **and** the manifest. What the fold actually left broken is not the
name but four delivery gaps: the frontmatter still says "in the current session" (so the
parallel-session mode is unroutable — a context-propagation defect by this repo's own standard),
there is no resume-cursor protocol, `## Status Log` records only shas so `_done_task_ids` cannot
derive the cursor, and the run-state FSM has never been initialized (`ls specs/*/RUN.json` → empty),
so every checkpoint is a swallowed no-op. Fixing those four is additive and keeps one source of
truth for the Step-0 gate and the ship gate.

### Alternatives considered

- **Resurrect `skills/executing-plans/SKILL.md` (full copy).** Rejected: requires un-pinning
  `RETIRED` in `scripts/check_slim_surface.py` + its test, manifest `skills[]` 12→13, and a second
  copy of the Step-0 gate and the receipt/ship gate. That drift already bit once — the old
  `/executing-plans` path never wrote `.review-receipt.json`, so `finishing-a-development-branch`
  Gate 0 blocked the push (recorded in local memory `executing-plans-needs-manual-review-receipt`).
- **Thin ~25-line wrapper skill under the old name.** Rejected by the user in favour of enhance-in-place;
  it still costs the guard un-pin and a manifest entry for a pure alias.
- **Discoverability-only fix (frontmatter + section order).** Rejected as insufficient: it makes the
  mode routable but leaves the resume cursor unspecified and the run-state no-op in place.

### Deviations

- Rule 3 — Added `skills/writing-plans/SKILL.md` to task 1.3's Files: its Execution Handoff pointed
  readers at the old "parallel session" name, which task 1.1's rename turned into a stale pointer.
  Plan amended rather than edited silently. Commit `<sha>`.
- Rule 1 — Step -1 source 2: documented that `run_state.py status` exit 3 means *no run was ever
  initialized*, not *plan untouched* (`not_observed != absent`); a resuming session would otherwise
  read an error as an absence. `skills/subagent-driven-development/SKILL.md`. Commit `<sha>`.
- Rule 1 — Step -1 source 3: defined `<base>` as the branch point (usually `main`); the bare
  placeholder was unresolvable for a session with no history — the exact context this step serves.
  `skills/subagent-driven-development/SKILL.md`. Commit `<sha>`.
- Rule 1 — `rules/wave-parallelism.md` step 2 referenced `## 7. Status Log`; the canonical section is
  `## 6. Status Log` (`rules/plan-format.md`) and consumers accept `## Status Log` or `## N. Status
  Log`. Corrected to the neutral form on the line being edited. Commit `<sha>`.
- Rule 3 — Added `specs/**/events.jsonl.lock` to `.gitignore`: this spec is the first live run-state
  run in the repo, so the fcntl lock file appeared as a tracked artifact for the first time. `RUN.json`
  and `events.jsonl` stay tracked (the durable record); the lock is machine-local. `hooks/blast-radius-check.sh`
  flagged `.gitignore` as outside the plan's Files set, so the plan was amended. Commit `<sha>`.
- Rule 1 — PLAN.md SC-1's check contained an escaped pipe inside a markdown table cell, so the
  command would have matched a literal `|` if copy-pasted; rewritten pipe-free per
  `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`. Commit `<sha>`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| behavior | `grep -q '^description:.*new session' skills/subagent-driven-development/SKILL.md` | 0 | resume mode is routable from the frontmatter alone | SC-1 |
| behavior | `grep -q 'Step -1' skills/subagent-driven-development/SKILL.md` | 0 | reconstruction step exists | SC-2 |
| behavior | `python3 -c "t=open('skills/subagent-driven-development/SKILL.md').read();import sys;sys.exit(0 if all(s in t for s in ['Status Log','run_state.py status','git log','SUMMARY.md']) else 1)"` | 0 | all four cursor sources named | SC-3 |
| behavior | `grep -q 'resume <slug>' skills/subagent-driven-development/SKILL.md` | 0 | invocable by argument, no new skill name | SC-4 |
| behavior | `grep -q 'task ids' rules/wave-parallelism.md` | 0 | Status Log contract tightened | SC-5 |
| behavior | `grep -q 'run_state.py init --slug' skills/subagent-driven-development/SKILL.md` | 0 | run initialized before first transition | SC-6 |
| behavior | `python3 -c "import sys;sys.path.insert(0,'skills/visual-planner');import render_plan as r;e=r.parse_status_entries('## Status Log' + chr(10)*2 + '- 2026-07-26 — tasks 1.1, 1.2 complete; commits abc1234, def5678' + chr(10));sys.exit(0 if r._done_task_ids(e,['1.1','1.2'])=={'1.1','1.2'} else 1)"` | 0 | documented entry shape really yields a cursor, against the live renderer | SC-7 |
| guard | `python3 scripts/check_slim_surface.py` | 0 | no retired skill returned to disk or manifest | SC-8 |
| registry | `python3 scripts/check_manifest.py` | 0 | skills[] still 12, bidirectionally consistent | SC-9 |
| lint | `bash scripts/lint-doc-truth.sh` | 0 | no dangling path in CLAUDE.md / skills/README.md / rules/ | SC-10 |
| lint | `bash scripts/lint-skill-bash.sh` | 0 | the added `run_state.py init` block is shellcheck-clean | |
| lint | `python3 scripts/check_verify_rows.py specs/new-session-plan-resume` | 0 | all PLAN/SUMMARY rows pipe-free and <60s | |
| suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN — 217 python + every hook/script suite | |
| dogfood | `grep -q '3/3 done' specs/new-session-plan-resume/PLAN.md` | 0 | this plan's own Status Log entry, written in the new shape, moved the derived Progress cursor 0/3 → 3/3 — the capability proven end-to-end on itself | SC-7 |

### Rollback

- `git revert <sha>` — all four changes are documentation/prompt edits under `skills/` and `rules/`;
  no schema, no hook registration, no script behavior. Reverting restores the current fold verbatim.

### Review

Run inline by the main session, not as independent subagents — this session was instructed not to
dispatch agents, so the ensemble diversity the skill's contract assumes was **not** available. What
was actually run, honestly scoped:

- **context-propagation audit (inline).** Consumers of the changed instructions enumerated:
  main-session controller (delivery proven — Skill tool loads the whole `SKILL.md`), new-session
  controller (same mechanism; the frontmatter fix is what makes it *reachable*), implementer
  subagents (unaffected — no implementer-facing instruction changed), reviewers/scorers (unaffected),
  and `render_plan.py` as the machine consumer of the Status Log contract (delivery proven
  behaviorally by SC-7). **One delivery condition stands:** sessions load
  `.claude/skills/…`/`.claude/rules/…`, so none of this reaches a live session until
  `scripts/deploy-harness.sh` runs. Not done here — mutating `.claude/` needs explicit human
  confirmation.
- **correctness pass (inline).** Three findings, all fixed above (Rule-1 deviations: run_state
  exit-3 semantics, `<base>` undefined, the escaped-pipe SC command). `init` idempotency was checked
  live, not assumed: the second call printed `already initialized`.
- **intent pass (inline).** Against the verbatim `### Intent`: no `gap` (research + opinion
  delivered, capability restored, workflow unbroken), no `excess` beyond the Rule-3 addition recorded
  above. The user's literal words asked to bring back the *skill*; they then chose enhance-in-place
  over the file, which is why no `skills/executing-plans/` exists — recorded here so the divergence
  is deliberate and auditable, not drift.

No `.review-receipt.json` was written: the receipt asserts independent reviews ran, and these were
not independent. `finishing-a-development-branch` Gate 0 will therefore (correctly) block a push
until the real chain is run.

### Harness-Delta

- backlog — `specs/STATE.md:24` and `templates/structure/specs-STATE.md:24` both advertise a
  `/session-tracker` skill that does not exist on disk (verified: not in `skills/`, not in
  `harness-manifest.json`). Resume guidance now lives in `subagent-driven-development`; those two
  lines should point there instead. Out of scope here → `/compound`.
- fix-direct — the durable run-state had **never** been initialized on any spec (`ls specs/*/RUN.json`
  was empty across ~60 specs) because only `feature-intake` calls `init` and every downstream
  `transition` is `|| true`. This spec is the first live run (`RUN.json` + `events.jsonl` at
  `specs/new-session-plan-resume/`), and task 1.1's added `init` closes the hole for specs that
  reach execution without intake.
