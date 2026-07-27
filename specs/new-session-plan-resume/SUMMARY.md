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
   the exit-3 contract at the `implementing` checkpoint with an explicit **prohibition** on calling
   `init` there (a fresh `init` lands in `queued`, and `queued -> implementing` is not a legal FSM edge,
   so it would produce a stuck run instead of an untracked one — see `### Review`).
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
derive the cursor, and no spec had ever been run-state-initialized (`ls specs/*/RUN.json` → empty), so
every checkpoint was a swallowed no-op. Fixing those four is additive and keeps one source of truth for
the Step-0 gate and the ship gate. Gap 4 is closed by *disclosure*, not by forcing state: the
checkpoint now documents the exit-3 case and forbids `init` there (see `### Review` for why the first,
`init`-based attempt was wrong), and `/feature-intake` remains the single owner of `init` — which is
how this spec became the repo's first live run.

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
  Plan amended rather than edited silently. Commit `bdd4acf`.
- Rule 1 — Step -1 source 2: documented that `run_state.py status` exit 3 means *no run was ever
  initialized*, not *plan untouched* (`not_observed != absent`); a resuming session would otherwise
  read an error as an absence. `skills/subagent-driven-development/SKILL.md`. Commit `bdd4acf`.
- Rule 1 — Step -1 source 3: defined the base ref; the bare `<base>` placeholder was unresolvable for
  a session with no history — the exact context this step serves.
  `skills/subagent-driven-development/SKILL.md`. Commit `bdd4acf`.
- Rule 1 — Step -1 source 3 (second pass, found by *running* the recipe): "`<base>` is the branch
  point (usually `main`)" produced a 100+ commit dump in this repo, because branches here are cut
  from the `loop` integration branch. Replaced with `$(git merge-base HEAD <base-branch>)` plus the
  wrong-base heuristic (output much longer than the task count ⇒ wrong base).
  `skills/subagent-driven-development/SKILL.md`. Commit `7bfc604`.
- Rule 1 — `rules/wave-parallelism.md` step 2 referenced `## 7. Status Log`; the canonical section is
  `## 6. Status Log` (`rules/plan-format.md`) and consumers accept `## Status Log` or `## N. Status
  Log`. Corrected to the neutral form on the line being edited. Commit `bdd4acf`.
- Rule 3 — Added `specs/**/events.jsonl.lock` to `.gitignore`: this spec is the first live run-state
  run in the repo, so the fcntl lock file appeared as a tracked artifact for the first time. `RUN.json`
  and `events.jsonl` stay tracked (the durable record); the lock is machine-local. `hooks/blast-radius-check.sh`
  flagged `.gitignore` as outside the plan's Files set, so the plan was amended. Commit `bdd4acf`.
- Rule 1 (caught by the ship gate re-running the table) — Two bookkeeping defects in this SUMMARY's
  own `### Verify` table: the exit-3 contract row was tagged `SC-6` whose `Expected` is `exit 0`
  (SC-FAIL — untagged, since the row asserts a non-zero contract), and a `bash scripts/run-tests.sh`
  row TIMEOUT-ed against the 60s cap (removed — whole-suite rows are banned per
  `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`; the ALL GREEN result is
  recorded in `PLAN.md ## Status Log` instead). Note `scripts/check_verify_rows.py` passed both rows —
  only `verify_summary.py --check`, which actually executes them, caught it. Commit `3df5366`.
- Rule 1 (blocking, caught by the correctness pass) — Removed the `run_state.py init --slug <slug>
  || true` line that task 1.1(d) had added before the `implementing` transition: proved by running the
  real engine that `init` lands in `queued` and `queued -> implementing` is not a legal edge, so the
  transition failed exit 2, `|| true` swallowed it, and the run stayed `queued` while implementing —
  a wrong state where there had merely been a missing one. Replaced with the exit-3 semantics plus an
  explicit prohibition; SC-6 rewritten to assert the correct behavior.
  `skills/subagent-driven-development/SKILL.md`, `specs/new-session-plan-resume/PLAN.md`. Commit `3df5366`.
- Rule 1 — PLAN.md SC-1's check contained an escaped pipe inside a markdown table cell, so the
  command would have matched a literal `|` if copy-pasted; rewritten pipe-free per
  `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`. Commit `bdd4acf`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| behavior | `grep -q '^description:.*new session' skills/subagent-driven-development/SKILL.md` | 0 | resume mode is routable from the frontmatter alone | SC-1 |
| behavior | `grep -q 'Step -1' skills/subagent-driven-development/SKILL.md` | 0 | reconstruction step exists | SC-2 |
| behavior | `python3 -c "t=open('skills/subagent-driven-development/SKILL.md').read();import sys;sys.exit(0 if all(s in t for s in ['Status Log','run_state.py status','git log','SUMMARY.md']) else 1)"` | 0 | all four cursor sources named | SC-3 |
| behavior | `grep -q 'resume <slug>' skills/subagent-driven-development/SKILL.md` | 0 | invocable by argument, no new skill name | SC-4 |
| behavior | `grep -q 'task ids' rules/wave-parallelism.md` | 0 | Status Log contract tightened | SC-5 |
| behavior | `python3 -c "t=open('skills/subagent-driven-development/SKILL.md').read();import sys;sys.exit(0 if 'Do not' in t and 'queued -> implementing' in t and 'FORWARD_TRANSITIONS' in t else 1)"` | 0 | uninitialized run reported untracked, never forced into a wrong state | SC-6 |
| behavior | `python3 runtime/run_state.py transition --slug probe-nonexistent --to implementing --event x` | 3 | asserts the exit-3 contract Step -1 and Step 1 both document (missing run, not a stuck one). Deliberately untagged: SC-6 expects exit 0, this row asserts a non-zero contract | |
| behavior | `python3 -c "import sys;sys.path.insert(0,'skills/visual-planner');import render_plan as r;e=r.parse_status_entries('## Status Log' + chr(10)*2 + '- 2026-07-26 — tasks 1.1, 1.2 complete; commits abc1234, def5678' + chr(10));sys.exit(0 if r._done_task_ids(e,['1.1','1.2'])=={'1.1','1.2'} else 1)"` | 0 | documented entry shape really yields a cursor, against the live renderer | SC-7 |
| guard | `python3 scripts/check_slim_surface.py` | 0 | no retired skill returned to disk or manifest | SC-8 |
| registry | `python3 scripts/check_manifest.py` | 0 | skills[] still 12, bidirectionally consistent | SC-9 |
| lint | `bash scripts/lint-doc-truth.sh` | 0 | no dangling path in CLAUDE.md / skills/README.md / rules/ | SC-10 |
| unit | `python3 -m pytest runtime/test_run_state.py -k "never_initialized or missing_projection" -q` | 0 | 2 passed — pins both run-state branches Step -1 must distinguish | SC-11 |
| unit | `python3 -m pytest runtime/test_run_state.py -k "blocked_to_implementing or projection_without_event_log" -q` | 0 | 2 passed — pins the blocker-erasure path and the log-less projection | SC-12 |
| unit | `python3 -m pytest runtime/test_run_state.py -k terminal_run_rejects -q` | 0 | 1 passed — terminal run rejects the checkpoint at the CLI layer (exit 2, state unchanged) | SC-13 |
| unit | `python3 -m pytest runtime/test_run_state.py -k covers_every_run_state -q` | 0 | 1 passed — all 16 states classified; mutation-checked (dropping `verifying` fails with "does not classify: ['verifying']") | SC-14 |
| unit | `python3 -m pytest runtime/test_run_state.py -k only_planning_and_interrupts -q` | 0 | 1 passed — pins that only `planning`/`blocked`/`escalated` reach `implementing` in one hop, and that the skill instructs the walk; mutation-checked against the skill text | SC-15 |
| unit | `python3 -m pytest runtime/test_run_state.py -k shipped_plan_stop_exempts -q` | 0 | 1 passed — shipped-plan rule stays scoped to plan tasks and keeps exempting `fixing_ci` / `addressing_review`; mutation-checked | SC-16 |
| lint | `bash scripts/lint-skill-bash.sh` | 0 | the edited run-state bash block is shellcheck-clean | |
| lint | `python3 scripts/check_verify_rows.py specs/new-session-plan-resume` | 0 | all PLAN/SUMMARY rows pipe-free and <60s | |
| dogfood | `grep -q '3/3 done' specs/new-session-plan-resume/PLAN.md` | 0 | this plan's own Status Log entry, written in the new shape, moved the derived Progress cursor 0/3 → 3/3 — the capability proven end-to-end on itself | SC-7 |

### Rollback

- `git revert <sha>` — all four changes are documentation/prompt edits under `skills/` and `rules/`;
  no schema, no hook registration, no script behavior. Reverting restores the current fold verbatim.

### Review

Four reviewers were dispatched as independent read-only subagents on a different model (`reviewer`
agent type, model `sonnet`, range `6cc968b..94e3da9`): context-propagation audit, correctness, intent,
simplicity. **All four went idle without returning a report**, so their conclusions are not available
and are not claimed here. The passes below were then executed by the main session with mechanical
verification. This is weaker than the skill's contract (no ensemble diversity) and is recorded as
such rather than papered over.

**Blocking finding, found and fixed (correctness):** the first version of task 1.1(d) added
`run_state.py init --slug <slug> || true` before the `implementing` transition. Proved wrong by
running it against the real engine in a throwaway specs root:

```
init                         -> state=queued, exit 0
transition --to implementing -> "queued -> implementing is not a valid transition", exit 2  (swallowed by || true)
status                       -> state: queued        <- stuck there permanently
```

`queued -> implementing` is not an edge in `runtime/run_state.py` `FORWARD_TRANSITIONS`, so the added
`init` converted an honest *absence* of run state into a *wrong* one — `list --active` would report
`queued` for a spec being actively implemented. Fixed by removing the `init` and instead documenting
the exit-3 case plus an explicit prohibition (`/feature-intake` owns `init`). SC-6 asserted the wrong
requirement and was rewritten to assert the correct behavior; task 1.1(d) records the reversal.

**Audit (mechanical parts, run):** no live reference to the removed `## Parallel session` name
survives outside `specs/**` and `docs/research/**` (verified by repo-wide grep); no hook depends on
wording this diff changed (`hooks/*.sh` grep for `Status Log` / `Parallel session` → none); the Status
Log contract is delivered to its machine consumer, proven behaviorally by SC-7 against the live
`render_plan.py`.

**External review (Codex, PR #173, reviewed commit `9365fbf`) — the outside-the-harness pass the
local oracles cannot substitute for. Two P2 findings:**

- **P2-1 CONFIRMED and fixed.** Step -1 omitted `specs/STATE.md`, which is exactly where
  `rules/wave-parallelism.md` → Collection protocol step 4 writes a **paused wave's blocker cursor**.
  The other four sources can show a task as merely *not started* when it is in fact *blocked*, so a
  resuming session could re-enter a blocked task instead of reporting `blocked`. Added as source 5
  (scoped to the `## Active Spec` block; the Session End Log breadcrumbs are session noise). Verified
  against ground truth before accepting: `grep -n "STATE.md" rules/wave-parallelism.md` → line 57
  writes it, `grep -c "STATE.md" skills/subagent-driven-development/SKILL.md` → **0** reads of it.
  Note the local review chain and the inline passes both missed this, including while *editing* that
  very step-4 line — the finding is the reviewer's, not a re-discovery.
- **P2-2 resolved by automation; reviewer lacked the later commit.** It flagged `RUN.json` committed at
  `verifying` for a shipped plan, permanently advertised by `run_state.py list --active` via
  `hooks/session-knowledge.sh`. The state advanced to `ready_to_merge` in the commit after the one
  reviewed, and `.github/workflows/post-merge-maintenance.yml:28,77-87` triggers on
  `branches: [main, loop]` and performs the terminal `--to shipped` transition on merge. `ready_to_merge`
  is the correct non-terminal state for a PR awaiting merge, so no change made.

**Codex round 2 (reviewed commit `02e27a8`) — both P2s land on the source-5 text round 1 produced.
Both CONFIRMED against live evidence and fixed:**

- **P2-3 — `specs/STATE.md` is a global slot; match the slug before consuming it.** The round-1 fix
  told a resuming session to read the `## Active Spec` blocker without checking whose spec it belongs
  to. Live counter-example in this very repo: that block currently names `review-chain-benchmark`,
  `Updated: 2026-07-15` — a *different* spec, 12 days stale — so resuming spec A would have imported
  spec B's blocker. Now gated on `- **Slug:**` matching `<slug>` and a non-stale `- **Updated:**`,
  with the reason stated: sources 1–4 are slug-scoped, this is the only one that can lie about whose
  state it is.
- **P2-4 — a `paused` plan must be reactivated or blast-radius protection stays off.** Step 1's
  transition was written `proposed → active` only, and `hooks/blast-radius-check.sh:32,38` states
  `status: active` is the ONLY thing that arms the hook. Resuming a parked plan would therefore have
  run the whole batch with blast-radius silently disarmed. Fixed in both places: Step 1 now reads
  "from `proposed` on a first run, or from `paused` when resuming", and Step -1 states the requirement
  explicitly before dispatch.

**Codex round 3 (reviewed commit `7a02fc4`) — 1 P2, CONFIRMED and fixed:**

- **P2-5 — exit 3 conflated "never initialized" with "corrupt storage".** `runtime/run_state.py:32-33`
  defines 3 as *missing/**corrupt** storage or I/O failure*, but the text said exit 3 means the run was
  never initialized. A damaged tracked run would therefore be read as an absent one, silently
  discarding a real `blocked` / `waiting_on` state before resuming. Verified empirically — the two
  worlds are distinguishable by message, which is now what the skill tells you to read:

  | Case | Output | Exit |
  |---|---|---|
  | never initialized | `missing: specs/<slug>/RUN.json` | 3 |
  | `RUN.json` corrupt | `corrupt JSON in specs/<slug>/RUN.json: …` | 3 |
  | `events.jsonl` corrupt behind a valid projection | normal state output | **0** |

  Fixed in both places (Step -1 source 2 and the Step 1 checkpoint): `missing:` → fall back to the
  other four sources; any other exit-3 message → try `rebuild --slug <slug>`, and if that also reports
  corruption, **stop and surface it** rather than resume on a guess. The third row is called out too,
  since `status` reads the projection and cannot see a corrupt event log.

**Codex round 4 (reviewed commit `4665c7f`) — 1 P2, CONFIRMED and fixed:**

- **P2-6 — round 3 *documented* the projection blind spot instead of closing it.** Both halves of the
  finding check out against the code: `cmd_transition` appends + `fsync`s the event **before**
  `atomic_write_json(RUN.json, …)` (`runtime/run_state.py`, transition body), so an interruption between
  those two writes leaves `events.jsonl` ahead of the projection; and `rebuild --check` exists as a
  genuinely non-mutating validator. Reproduced end-to-end — a stale projection hid a real blocked run:

  ```
  status                 → state: investigating, resume_event: None, exit 0   ← looks healthy
  rebuild --slug --check → DRIFT: RUN.json does not match events.jsonl, exit 3
  rebuild --slug         → rebuilt (seq=3);  status → state: blocked, resume_event: unblock
  ```

  A resuming session would have treated a `blocked` run as merely unstarted, and no other cursor source
  can recover FSM state. Step -1 source 2 now **requires** `rebuild --slug <slug> --check` during
  reconstruction: exit 0 confirms the projection, `DRIFT` routes to a reproject-then-re-read, a
  corruption message stops the resume.

**Codex round 5 (reviewed commit `1ae652d`) — 1 P2, CONFIRMED and fixed, plus the regression it asked
for:**

- **P2-7 — the round-4 `--check` was unconditional, and exit-3 `missing:` is ambiguous.** Verified both
  branches by running them:

  | Case | `status` | `rebuild --check` | Truth |
  |---|---|---|---|
  | legacy: no `events.jsonl`, no `RUN.json` | `missing: RUN.json` exit 3 | `missing: events.jsonl` exit 3 | never initialized |
  | valid `events.jsonl`, `RUN.json` gone | `missing: RUN.json` **exit 3 — same message** | `missing: RUN.json` exit 3 | `rebuild` recovers `state: blocked`, `resume_event: unblock` |

  So `status`'s message cannot separate "never initialized" from "projection lost", and the previous
  text's `missing:` branch would have discarded recoverable FSM state — while a plain legacy resume got
  an unexplained second exit 3. Source 2 now branches on **whether `events.jsonl` exists** (the real
  discriminator): absent → skip validation entirely; present with no projection → `rebuild`, then
  re-read `status`; both present → the round-4 `--check`.
- **Regression added** (`runtime/test_run_state.py`, +2 tests, suite 217 → **219**):
  `test_never_initialized_run_is_not_checkable` and
  `test_missing_projection_over_valid_log_recovers_blocked_state` — the latter asserts the recovered
  projection really carries `blocked` / `unblock`, so the branch cannot silently regress into
  prose-only. Pinned as **SC-11**. This is the repo's own preference over documentation:
  *prefer a deterministic check you can ship over a reviewer you cannot assume exists.*

**Codex round 6 (reviewed commit `db094f9`) — 2 P2, both CONFIRMED and fixed. The first is the most
serious finding of all six rounds: it destroys data.**

- **P2-8 — resuming a `blocked` run silently erased the blocker.** Step -1 said to report the cursor
  and continue; nothing downstream stopped that. `valid_targets` deliberately lets an interrupt state
  enter **any** active state, so Step 1's `transition --to implementing` succeeds, and the new event —
  carrying no `waiting_on` / `resume_event` of its own — wipes both from the projection. Run live:

  ```
  before  state: blocked      waiting_on: PR #999   resume_event: dep-merged
  after   state: implementing waiting_on: None      resume_event: None      (exit 0)
  ```

  The record of *why* work was paused, gone — and the resumed batch proceeds as if nothing was blocked.
  Step -1 now **STOPs** on `blocked` / `escalated` until the recorded resume condition is confirmed.
- **P2-9 — `RUN.json` without `events.jsonl` was classified as "never initialized".** The round-5
  branch keyed on the absence of `events.jsonl` alone. But with the projection still present, `status`
  exits **0** and reports a state — including a `blocked` one with a `resume_event` — while that
  projection can no longer be rebuilt or verified. The legacy case now requires **both** files absent;
  a projection with no log behind it is treated as storage corruption → stop.
- **Regression added** (`runtime/test_run_state.py`, +2 tests, suite 219 → **221**), pinned as **SC-12**:
  `test_blocked_to_implementing_clears_blocker_metadata` (asserts the erasure, so if the engine ever
  forbids that edge the skill's stop rule can be relaxed on evidence) and
  `test_projection_without_event_log_is_unrebuildable`.

**Codex round 7 (reviewed commit `97dc642`) — 1 P2, CONFIRMED and fixed:**

- **P2-10 — a terminal run (`cancelled` / `superseded` / `shipped`) fell through into task resumption.**
  Round 6 added stop rules for `blocked` / `escalated` but not for the terminal states. Run live, the
  rejection is real and then hidden:

  ```
  transition --to implementing            → "cancelled is terminal; no further transitions", exit 2
  transition --to implementing || true    → exit 0        ← rejection invisible
  status                                  → state: cancelled (unchanged, while the session edits on)
  ```

  So a plan someone deliberately cancelled — or one already shipped — could be edited and sent through
  the shipping flow with its run frozen. Step -1 now STOPs on terminal states and states explicitly that
  the checkpoint's non-fatal guard is not permission.
- **Regression added** (suite 221 → **222**), pinned as **SC-13**:
  `test_terminal_run_rejects_resume_transition_at_cli`. Deliberately **not** a duplicate of the existing
  `test_terminal_state_blocks_transition`, which asserts `valid_targets` / `validate_transition` at the
  *unit* level and never goes through `main()` — the CLI exit code is precisely the layer the non-fatal
  guard silences, so that is the layer this rule depends on and the layer now pinned.
- Also caught while writing SC-13: its Behavior cell originally contained an escaped pipe (the same
  markdown-table hazard as the earlier SC-1 defect). Reworded pipe-free before committing.

**Closing the pattern, not the next instance (user-directed, after round 7).** Four of the seven review
rounds found the same shape of defect: *a run state the resume path could encounter but did not branch
on*, with Step 1's non-fatal `|| true` hiding the consequence each time. Patching the fifth instance
would have repeated the mistake, so Step -1 now carries an **exhaustive 16-state table** — the 11 active,
2 interrupt and 3 terminal states of `runtime/run_state.py`, each with an explicit verdict
(proceed / proceed-elsewhere / stop) and its reason. Notably this classified four states no reviewer had
raised yet: `awaiting_confirmation` (a pending human decision), `awaiting_ci`, `awaiting_review` and
`ready_to_merge` — the last three all have a CI run, a review, or a receipt in flight that a fresh commit
would invalidate.

The durable part is the guard, not the table: `test_step_minus_one_covers_every_run_state` reads the
skill's own table and fails when `rs.ALL_STATES` gains a member it does not classify. **Mutation-checked**
rather than assumed — dropping `verifying` from the table fails with
`resume recipe does not classify: ['verifying']`, so the assertion is not vacuous. Pinned as **SC-14**.

Process note, recorded because it cost real work: while proving that guard bites, `git checkout --` was
used to undo the mutation and silently discarded the uncommitted table with it. The table had to be
re-authored. Mutate a **copy** when the working tree holds unstaged work.

**Codex round 8 (reviewed commit `221840d`) — 1 P2, CONFIRMED and fixed. It landed inside the
"pattern closure" itself, and that is the most useful thing the review produced:**

- **P2-11 — a state can be *classified* and still have no legal path to the checkpoint's target.** The
  16-state table gave `queued`, `investigating` and `planning` one shared verdict ("Proceed to Step 0"),
  but `FORWARD_TRANSITIONS` allows only `queued → investigating` and
  `investigating → {awaiting_confirmation, planning}`. So from the first two, Step 1's
  `transition --to implementing` exits 2, `|| true` hides it, and the run stays stale while
  implementation proceeds. Run live:

  ```
  state: queued  →  transition --to implementing  →  "queued -> implementing is not a valid
                                                      transition", exit 2  →  || true → exit 0
  state after: queued        (stale, while the batch runs)
  legal walk:  queued → investigating → planning → implementing   ✓
  ```

  `queued` / `investigating` now get their own row: proceed with the *work*, but walk the run state one
  legal hop at a time to `planning` first.
- **The guard was the real defect.** `test_step_minus_one_covers_every_run_state` asserted every state is
  *mentioned* — not that a "proceed" verdict is *reachable*. That is the same blind spot one level up:
  exhaustive enumeration of states, with no check against the transition graph. Fixed by
  `test_only_planning_and_interrupts_reach_implementing_directly`, which pins the exact one-hop set
  (`{planning, blocked, escalated}` — computed, not assumed), proves the walk works from `queued`, and
  asserts the skill instructs it. Mutation-checked on a **copy** this time: replacing the walk sentence
  fails the test. Pinned as **SC-15**.

**Codex round 8.5 (review on `f4ea405`) — MISSED on the first pass, then fixed.** Two reviews arrived
between round 7 and round 8 and only the later one was handled; this one was skipped. Its finding was
still live: the STOP rows keyed on **run state** only, while `finishing-a-development-branch` Step 4 marks
`PLAN.md` `status: shipped` **before** the push — so a plan sits `shipped` with its PR still open (this
spec's own `PLAN.md` is the live example). A resumed session would then execute tasks against shipped
work, with two failures at once: new commits invalidate the review receipt, and
`hooks/blast-radius-check.sh` stays disarmed because the plan is not `active`. Step -1 now checks the
**plan** lifecycle alongside the run state and stops on a `shipped` plan whose branch is unmerged.

**Codex round 9 (reviewed commit `d102290`) — CONFIRMED, split between a fix here and issue #174.**

- The round-4 claim that `rebuild --check` validates the run state **over-promised**. `read_events`
  checks required-key presence and `project` is a blind fold — no `seq` continuity, no `from_state`
  chaining, no `slug`/`run_id` consistency, no transition legality. Verified by forging a log whose keys
  are all present but whose history is impossible (`queued` at `seq 1`, then `shipped` also at `seq 1`
  with `from_state: verifying` and a different `run_id`):

  ```
  rebuild         → rebuilt RUN.json from events.jsonl (seq=1)   exit 0
  rebuild --check → RUN.json matches events.jsonl (seq=1)        exit 0
  status          → state: shipped  seq: 1  run_id: r1  sha: deadbee
  ```

  A projection stitched from two different runs, reporting a terminal state its history cannot reach —
  and `--check` calls it a match, because "matches" means *projection equals fold(log)*, nothing more.
- **Fixed here (prompt side):** Step -1 now states exactly what `--check` proves and what it does not,
  and requires the reader to sanity-check the projection — a state the plan's history cannot explain, a
  `seq` that does not advance, or a `sha` absent from `git log` means stop, exit 0 notwithstanding.
- **Deliberately NOT fixed here (engine side):** chain validation belongs in `runtime/run_state.py`,
  a core engine and a Rule-4 high-blast file, and is unrelated to this PR's intent (resume mode).
  Bundling it would be exactly the `excess` that `/intent-review` exists to catch. Filed as
  **issue #174** with the reproduction, the suggested direction (validate in `read_events`, fail
  `StorageError`/exit 3 so every existing caller inherits it), and the compatibility question that
  should be settled first.

**Codex round 10 (reviewed commit `f3df0cf`) — 1 P2, CONFIRMED and fixed. The finding is a
contradiction the previous fix introduced.**

- The round-8.5 plan-lifecycle rule was written as a blanket stop ("a `shipped` plan … is not available
  for resumption: stop and report"), which contradicts the table two paragraphs above it, where
  `fixing_ci` and `addressing_review` are told to **proceed**. And those two states *necessarily* meet a
  shipped plan: `finishing-a-development-branch` marks the plan `shipped` at Step 3.1, ahead of the push
  (3.2) and the PR (3.4) — so a repair state, which only exists after the PR does, always finds
  `status: shipped`. Reading the rule as a full stop would block exactly the CI or review fix such a
  resume was started for.
- Fixed by scoping the rule to what it is actually about: a shipped plan bars **plan-task execution**,
  nothing else, with the two repair states named as explicit exemptions. Added the honest consequence
  too — during repair the plan is `shipped`, not `active`, so `hooks/blast-radius-check.sh` is not
  watching: keep those edits tight to the failing check.
- **Regression added** (suite 224 → **225**), pinned as **SC-16**:
  `test_shipped_plan_stop_exempts_the_repair_states` asserts the rule still says "not a blanket stop" and
  still names both repair states. Mutation-checked on a copy — re-broadening the rule fails it.

**Advisory, not fixed by design:** `specs/slim-skill-surface/PLAN.md:92` (SC-7) and its
`SUMMARY.md:109` Verify row grep for `"parallel session"` in
`skills/subagent-driven-development/SKILL.md` and now exit 1. That spec is `status: shipped` and
`scripts/ci-strict-gate.sh` only re-runs SUMMARYs **changed in the diff**, so nothing breaks. Editing a
shipped spec to match the present is exactly what `specs/slim-skill-surface/design.md` §4 refuses to
do to an audit trail — left as-is deliberately.

**Open delivery condition (audit finding 1, verified live):** `.claude/rules/wave-parallelism.md` and
`.claude/skills/subagent-driven-development/SKILL.md` still hold the pre-change copies (`diff` against
source differs), and live sessions load the `.claude/` copies. Nothing in this change reaches a running
session until `scripts/deploy-harness.sh` runs — not done here, since mutating `.claude/` needs
explicit human confirmation.

What was run before the reviewer dispatch, for completeness:

- **context-propagation audit (inline).** Consumers of the changed instructions enumerated:
  main-session controller (delivery proven — Skill tool loads the whole `SKILL.md`), new-session
  controller (same mechanism; the frontmatter fix is what makes it *reachable*), implementer
  subagents (unaffected — no implementer-facing instruction changed), reviewers/scorers (unaffected),
  and `render_plan.py` as the machine consumer of the Status Log contract (delivery proven
  behaviorally by SC-7). **One delivery condition stands:** sessions load
  `.claude/skills/…`/`.claude/rules/…`, so none of this reaches a live session until
  `scripts/deploy-harness.sh` runs. Not done here — mutating `.claude/` needs explicit human
  confirmation.
- **correctness pass (inline).** Three findings, all fixed (Rule-1 deviations: run_state
  exit-3 semantics, `<base>` undefined, the escaped-pipe SC command). `init` idempotency was checked
  live, not assumed: the second call printed `already initialized`. **This pass missed the blocking
  FSM defect above** — it verified that `init` is idempotent on an *existing* run and stopped there,
  never testing the `init`-then-`implementing` sequence on a *fresh* one. The second pass caught it
  only by running that exact sequence. Idempotency was the wrong question.
- **intent pass (inline).** Against the verbatim `### Intent`: no `gap` (research + opinion
  delivered, capability restored, workflow unbroken), no `excess` beyond the Rule-3 addition recorded
  above. The user's literal words asked to bring back the *skill*; they then chose enhance-in-place
  over the file, which is why no `skills/executing-plans/` exists — recorded here so the divergence
  is deliberate and auditable, not drift.

No `.review-receipt.json` was written: the receipt asserts independent reviews ran, and these were
not independent. `finishing-a-development-branch` Gate 0 will therefore (correctly) block a push
until the real chain is run.

### Harness-Delta

- backlog — **A review round can be skipped silently when two arrive back to back.** Reviews on
  `f4ea405` and `221840d` landed 9 minutes apart; only the later one was handled, and its finding stayed
  live for two more rounds. Handling reviews by "the latest one" is unsafe — the loop needs to track the
  last-handled review id per PR, not the last-seen commit. → `/compound`.
- backlog — **The review chain has no fallback when a dispatched reviewer returns no report.** All
  four reviewers dispatched here (`reviewer` agent type, model `sonnet`) went idle without delivering
  their findings text; follow-up `SendMessage` requests to three of them produced another idle
  notification and no report. The skill's contract assumes a returning subagent and says nothing about
  this failure mode, so the controller is left choosing silently between blocking forever and
  substituting a weaker inline pass. Two things are missing: an explicit instruction on what a
  no-report dispatch means (it is *not* a pass), and a receipt convention that distinguishes
  "reviewed independently" from "reviewed by the controller". This run recorded the distinction in
  prose because the receipt schema has no field for it. → `/compound`.
- backlog — `specs/STATE.md:24` and `templates/structure/specs-STATE.md:24` both advertise a
  `/session-tracker` skill that does not exist on disk (verified: not in `skills/`, not in
  `harness-manifest.json`). Resume guidance now lives in `subagent-driven-development`; those two
  lines should point there instead. Out of scope here → `/compound`.
- fix-direct — the durable run-state had **never** been initialized on any spec (`ls specs/*/RUN.json`
  was empty across ~60 specs) because only `feature-intake` calls `init` and every downstream
  `transition` is `|| true`. This spec is the first live run (`RUN.json` + `events.jsonl` at
  `specs/new-session-plan-resume/`), and task 1.1's added `init` closes the hole for specs that
  reach execution without intake.
