# gh-175-executable-resume-cursor — Summary

Lane: high-risk
Confidence: high
Reason: changes workflow-engine behavior (runtime resume authority + SDD skill) and the durable-state read contract; high-blast files (runtime/run_state.py, SKILL.md, harness-manifest.json).
Flags: workflow-engine, high-blast-file, public-contract
Affects: runtime/resume_decision.py, runtime/run_state.py, subagent-driven-development skill, harness-manifest.json
Input-type: spec slice

> `Lane` drives ceremony; `Confidence` drives interruption. Approved PLAN authored
> in PR #197; execution proceeds gated (per-task review + final chain).

### Intent

check PR https://github.com/minhtran3124/agent-harness/pull/197 and start implement

review lai docs, hiện tại có update mới và bắt đầu review plan để implement

## What changed

Completes issue #175 by turning `runtime/resume_decision.py` into the full evidence-driven
resume authority: one locked durable-state snapshot shared with status, a versioned JSON
lifecycle + per-task cursor contract over PLAN/run-state/git/SUMMARY/STATE, and portable
source/deployed wiring with a manifest contract and behavior-level integration tests.

### Rationale

Extend the single existing authority landed in PR #179 rather than adding a second
`resume_cursor.py` (design Option C): preserves progressive disclosure and one public entry
point. Completion is evaluated per task-mention (not per Status Log entry) after PR #197's
review round showed the renderer's entry-wide done set would wrongly mark a `Task 1.1
complete; Task 1.2 pending` entry as both-complete.

### Alternatives considered

- Add `scripts/resume_cursor.py` beside the runtime helper (Option B) — two public callables with
  overlapping state logic and immediate drift; rejected.
- Put blocker resolution + Verify execution into the helper (Option D) — crosses the
  mechanics/judgment boundary and runs plan-authored shell from a read-only path; rejected.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| snapshot/lock | `python3 -m pytest runtime/test_run_state.py -k "snapshot or readonly_lock" -q` | 0 | shared locked snapshot, torn-read guard | SC-1 |
| state/storage matrix | `python3 -m pytest runtime/test_resume_decision.py -k "state_matrix or storage_matrix" -q` | 0 | exact action+reason_code per state; exhaustive over FSM | SC-2 |
| shipped-plan | `python3 -m pytest runtime/test_resume_decision.py -k shipped_plan -q` | 0 | shipped blocks execute; repair still routes | SC-3 |
| interrupt recovery | `python3 -m pytest runtime/test_resume_decision.py -k "interrupt or waiting_origin" -q` | 0 | recovered waiting_on + successors | SC-4 |
| cursor/git evidence | `python3 -m pytest runtime/test_resume_decision.py -k "cursor or git_evidence" -q` | 0 | md+xml ordered cursor; checks_to_rerun; conflict stops | SC-5 |
| state hint/deviations | `python3 -m pytest runtime/test_resume_decision.py -k "state_hint or deviations" -q` | 0 | slug/≤7d STATE; deviations advisory | SC-6 |
| schema/readonly | `python3 -m pytest runtime/test_resume_decision.py -k "schema or readonly" -q` | 0 | v1 JSON; canonical bytes unchanged | SC-7 |
| deployed consumer | `bash tests/scripts/runtime-sync.test.sh` | 0 | exact deployed command → valid JSON | SC-8 |
| manifest contract | `python3 scripts/check_manifest.py` | 0 | resume-cursor-decision registered, no drift | SC-9 |
| SDD behavior contract | `bash tests/scripts/sdd-resume-cursor.test.sh` | 0 | routes all public actions by output, no prose anchors | SC-10 |
| plan-contract | `python3 scripts/check_plan_contract.py specs/gh-175-executable-resume-cursor/PLAN.md` | 0 | preflight | |

### Intent Findings

Intent review (plan-blind, opus-5, over `ba964a3..00b513b`): ✅ no divergence. Every SC clause
traces to an implemented outcome; no excess scope (CLI surface is only `--slug`/`--base`; module
performs no writes); the completion parser and base/range validation both trace to SC-5 + design.

### Not auto-verified

- Semantic read-only claim (helper never mutates canonical evidence) — reached traceability via
  before/after byte snapshots in the test suite; not independently re-run by a gate.
- Task 1.1 stderr message precedence on the untested edge "events.jsonl illegal AND RUN.json absent"
  now surfaces `invalid event chain` (was `missing: RUN.json`); exit 3 unchanged, #174 validation
  fires earlier. Reached truth for exit code (86-test suite); the specific message shift is a
  Minor untested-edge deviation, pinned only by the new snapshot tests, not by a dedicated
  regression test.
- Task 2.1 completion heuristic is marker-based: `_COMPLETE_RE` matches `\bdone\b` while
  `_NONCOMPLETE_RE` omits soft/future markers ("waiting", "will be"). A contrived Status Log
  segment like `Task 1.2 — waiting; will be done next` would wrongly mark 1.2 claimed_complete.
  Blast radius bounded — 1.2's Verify still lands in `checks_to_rerun`, fails, and routes to repair.
  Design §5.4 only mandates the explicit markers (pending/in-progress/blocked), which ARE handled.
  Minor; forwarded to final review.
- Task 2.1 read-only byte snapshots cover RUN.json/events.jsonl/PLAN.md for every action family
  (incl. rebuild) but not SUMMARY.md/STATE.md, which the decision path also reads. Those reads are
  read-only by construction (`_read_deviations`/`_read_state_hint`); the byte proof is narrower than
  the design's full canonical set. Minor; forwarded to final review.

### Context-Propagation Audit

Trigger: workflow-engine paths changed (SKILL.md, references/resume.md, harness-manifest.json).

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| Resume command (source-first + `.claude/runtime` fallback) | `subagent-driven-development` SKILL.md | fresh `resume <slug>` session (source or deployed) | always-loaded skill body (lines 13-24) | self-delivering body; deployed invocation proven by `tests/scripts/runtime-sync.test.sh` (SC-8) |
| `checks_to_rerun`-before-dispatch + `required_transition`-after-confirm | SKILL.md core | `execute-plan` session (does NOT trigger the on-demand reference Read) | always-loaded skill body (lines 26-28) | grep-confirmed present in core body, not only in references/resume.md |
| Repair/procedure detail | references/resume.md | manual-transition/repair session | explicit Read anchor in always-loaded body (line 30) | anchor present; no state table reintroduced (grep) |
| Action/reason_code vocabulary (6 codes) | SKILL.md branch list | any resume session | contract via `runtime/resume_decision.py` | helper emits exactly {execute-plan, resume-repair, resume-review-chain, wait, stop, rebuild}; matches skill branch list |
| `resume-cursor-decision` contract | check-contract-impact.sh / check_manifest.py | blast-radius tooling | registry entry in harness-manifest.json | `python3 scripts/check_manifest.py` exit 0 (all surface/consumer paths exist) |

**Verdict: PASS.** No load-bearing instruction is assumed/unconfirmed; each changed instruction is self-contained in the always-loaded skill body, anchored by an explicit Read, or a registry-linted manifest contract. No inline policy subset is unanchored.

### Correctness Review (adversarial, plan-blind)

Six independent finders over `ba964a3..e76b0fe`, then three fix rounds each re-reviewed
adversarially (regressions caught and closed): round 1 `401e1ce` (11 findings), round 2 `5842539`
(re-review found 3 new completion-parser regressions), round 3 `9b7ab60` + `<fix3b sha>` (strict
per-mention model replacing the leaky denylist; re-review found 2 more suppression regressions,
both closed with a separator-swept landmine test as the class guard). Final state: all blocking
findings resolved; full suite ALL GREEN; every adversarial shape verified at truth-tier.

Blocking findings (confirmed-real, reproduced), all fixed before ship:

- **[A/B] Parser parity (P1, resume_decision.py:141, 112-124):** `parse_tasks` sniffs `"<task" in ptext`
  on RAW text with no fence/inline-code masking and no markdown fallback. A markdown PLAN mentioning
  `<task` anywhere → 0 tasks → empty cursor → `execute-plan next_task:null` → skips every task.
  Reproduced: `specs/gh-121-spec-ticket-prefix/PLAN.md` render=7 tasks, resume=0.
- **[C] Status-Log completion parser (P1, :55, 195-211, 196):** `_TASK_MENTION` needs a `task(s)`
  keyword and binds only the first id; forward-only window; SHAs collected entry-wide. Multi-id/range
  entries (`Tasks 2.1, 2.2, 2.3 done`) under/over-claim; ~31-34 of ~49 real plans disagree with the
  renderer. Fix must keep the landmine closed (`Task 1.1 complete; Task 1.2 pending` → only 1.1).
- **[D] Non-dict RUN.json crash (P1, :599-600):** truthy non-dict projection → `AttributeError` →
  exit 3 no JSON, instead of structured `stop/storage-projection-only`. Reproduced (`[1,2]` → exit 3).
- **[E] SKILL.md stale-fallback (P1, SKILL.md:17-18):** `... 2>/dev/null || .claude/runtime/...` swallows
  a fail-closed exit-3 and re-answers from the gitignored deployed copy — confirmed STALE (pre-#175,
  no `snapshot_run_state`) → returns flat schema, no cursor → session dispatches unverified. Gate on
  source-file absence + require `schema_version==1`; do not blind-swallow stderr.
- **[F] Empty checks_to_rerun (P1, :363):** claimed-complete task with no Verify → `command:""` →
  the re-verify guard passes vacuously (fail-OPEN on the one safety mechanism). Emit a fail-closed
  `missing-verify` conflict.
- **[O] Unguarded read_text (P1, :69, 519, 547):** non-UTF-8/unreadable `STATE.md`/`SUMMARY.md`/`PLAN.md`
  → exit 3 kills the whole decision; STATE.md is repo-global. Advisory readers degrade to None+warning;
  PLAN read → structured `stop/plan-unreadable`.
- **[G] Unvalidated explicit/declared base (P2, :287-296, 310-319):** explicit `--base` and declared
  `VERIFY_ROWS_BASE`/`GITHUB_BASE_REF` fall through silently when unresolvable / no claimed commits;
  `resolve-base-ref.sh` errors loudly. Fail closed on an unresolvable declared base.
- **[I] `_derive_base` accepts ref==HEAD (P2, :256-268):** distance-0 candidate → empty range → false
  `git-evidence-conflict`. Skip rev-list-count-0 candidates.
- **[J] rev-list failure masked (P2, :331-332):** shallow-clone/`rev-list` failure → "nothing in range"
  → false conflict on healthy branch. Emit distinct `range-unavailable`.
- **[L] Status-Log entry folding (P2, :167-182):** an indent-0 non-bullet line folds into the prior
  entry and can complete it across the boundary. Only absorb indented continuations.
- **[H] `waiting_on` dropped from wait route (P2/P3, :672-679):** the blocker identity is no longer
  reported for `wait`; regression from BASE. Restore on the `awaiting-external` block.

Advisory (recorded, not blocking ship):
- **Pre-existing (not introduced by this work, same on base) — deferred, not auto-fixed on this
  branch per correctness-review scope discipline:** (a) a hyphen/en-dash range member (`Tasks
  1.1–1.4 shipped, 1.4 blocked`) is claimed even with its own explicit non-completion marker,
  because `_fill_range` members bypass per-mention suppression; (b) the progressive `executing`
  in `_COMPLETE_RE` reads as completion (`Executing task 1.2` → claimed) where render's vocabulary
  does not. Both are over-claims bounded by the `checks_to_rerun`/`missing-verify` fail-closed net;
  reached traceability (pinned by the adversarial battery, flagged here), not fixed.
- **[K] proposed/paused → action:execute-plan (:450-471):** design §5.6 sanctions an execution route
  carrying the required activation `required_transition`; the SKILL contract branches on `action`, so
  a stricter `stop/plan-activation-required` may be safer — flagged for maintainer, not auto-changed.
- **[M] cmd_status stderr precedence (run_state.py):** message-only shift, exit codes identical, no
  consumer parses it (see Task 1.1 note above).
- **[N] drift route reports fold state vs recorded state (:596-648):** P3 diagnostic; action unchanged.

### Rollback

- `git revert <implementation-sha>` — helper is read-only, no data migration; reverting restores
  PR #179 behavior. Do not remove or rewrite existing run logs during rollback.

### Harness-Delta

- none
