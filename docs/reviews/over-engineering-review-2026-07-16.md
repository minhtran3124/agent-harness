# Over-Engineering Review — harness-skills

- **Date:** 2026-07-16
- **Method:** Five parallel review agents, one per subsystem (skills/, hooks/+settings.json, scripts/+CI, rules/+templates/+governance docs, cross-cutting/system-level), each reading files in full and grepping for actual callers. Load-bearing claims were then independently re-verified in the main session (marked ✅ below).
- **Framing:** This is a solo-developer meta-repo (a Claude Code harness). "Over-engineering" here means: code/process whose cost (context tokens, maintenance, false positives, contradictions) exceeds what it prevents *for this repo's actual workload* — not merely "long files."

---

## 1. Executive summary

**Verdict: the architecture is sound in miniature; the instance is over-provisioned roughly 3–5× for its actual workload.** The core ideas are genuinely good — lane/confidence separation, signal-scaled artifacts, machine-read SUMMARY fields, mutation-tested hooks, the doc-truth lint. But the system has been optimizing itself faster than it gets used:

- **~13k tokens of always-on context per session** (CLAUDE.md + 7 auto-loaded rules + session-knowledge injection), plus ~25–30k more per full normal-lane feature chain.
- **8 of 12 knowledge-base entries document injuries the harness caused itself** (hook false positives, resync conflicts, its own scripts' bash bugs); **0 of 12** record an external application bug it prevented. ✅ (entries reviewed)
- **All of the last 40 commits are meta-work** — the harness improving the harness. It has not yet shipped a line of non-harness code.
- Roughly **a third of the hook code can never execute here** (targets an `app/` directory that doesn't exist ✅), **~1,050 lines of scripts have no caller or no enforcement point** ✅, and two skills contain **live contradictions that actively mislead an executing LLM** ✅.

**Counterweight (also verified):** the harness *is* dogfooded more than the failure log suggests — 33/33 specs carry a SUMMARY.md with real, non-placeholder Verify commands; the trust-metrics ledger has 32 substantive rows and is machine-read; `wave=` is used in 14 plans; ESCALATIONS was used 4 times with 3 real decisions. The waste is concentrated in *speculative* surfaces (templates never instantiated, dormant hooks, dead scripts) and *duplicated* prose — not in the core contract.

**Realistic total reduction with zero loss of enforced behavior:** ~1,000–1,100 lines from skills/, ~1,050 from scripts/, ~350+ from hooks/+tests, ~150 from rules/templates, and ~60% of the always-on context tax (~13k → ~5k tokens/session).

---

## 2. Correctness-level findings (fix these regardless of any simplification)

These are not style issues — they are contradictions or silent breakage found during the audit.

### C1. `writing-plans` teaches a plan format its own downstream gate rejects ✅ — HIGH
`skills/writing-plans/SKILL.md:57–108` mandates a superpowers-style plan header plus a `### Task N` step/checkbox task structure ("Write the failing test" steps, Python snippets). But `skills/executing-plans/SKILL.md:24–32` (Step 0 hard gate) and `rules/plan-format.md` require XML `<task><files><action><verify><done>` blocks — a plan written exactly per writing-plans **fails executing-plans' own validation gate** and renders an empty task list in PLAN.html (`render_plan.py` parses only `<task>` blocks). Also stale: `writing-plans:16` claims the worktree is "created by brainstorming skill" — brainstorming never creates worktrees.
**Fix:** delete the Task Structure + Plan Document Header sections; point at `rules/plan-format.md`. (~60 lines, removes the contradiction.)

### C2. `brainstorming`'s HARD-GATE contradicts feature-intake's lane routing ✅ — HIGH
`skills/brainstorming/SKILL.md:12–18`: "Every project goes through this process… regardless of perceived simplicity." But feature-intake routes tiny/normal lanes *around* brainstorming, and `skills/README.md` says "Skip /brainstorming when intent is clear." Two skills claim gate authority over the same decision.
**Fix:** delete the "Too Simple To Need A Design" block; state that brainstorming applies only when intake routes to it.

### C3. Post-merge bookkeeping pipeline silently dead ✅ — MEDIUM
`.github/workflows/post-merge-maintenance.yml:22` fires only on `branches: [v2]`, but PRs now merge to `main` (CI itself runs on `main`; PR #66 merged to main 2026-07-16; VERSION frozen at 2.0.0). `bookkeeping.sh` (119 lines) + the audit-trend JSONL are inert, and the workflow's comment explaining why main is *deliberately excluded* is stale doctrine.
**Fix:** one line (`branches: [main]`) — or take it as evidence the 3-artifact auto-bookkeeping pipeline exceeds solo-repo needs and retire it.

### C4. The documented risk-corroboration false positive is still unfixed — MEDIUM
`docs/solutions/harness/risk-corroboration-scans-test-comments-for-auth-words.md` (confirmed 2026-07-10) documents that English words like "session"/"permission" in comments under `tests/` trip the auth hard gate. `hooks/risk-corroboration.sh:71`'s pathspec excludes md/docs/specs/skills/hooks/.claude — but not `tests/`. The harness wrote itself a failure memo and then didn't apply it.
**Fix:** add `:!tests/` to the pathspec.

### C5. "Deny-on-no-response" escalation gate is unenforced fiction — HIGH (honesty of the model)
No hook or script reads `ESCALATIONS.md` (`grep -rl ESCALATIONS hooks scripts` → nothing). Proof it fails in practice: `specs/resync-protected-files/ESCALATIONS.md` E001 sits at `decision: pending` while its PLAN.md is `status: shipped` (PR #50). Yet the template, HARNESS.md §3.3, and orchestration.md all assert a blocking gate.
**Fix:** either a ~5-line check in `commit-quality-gate.sh` (fail on `decision: pending`), or delete the "deny-on-no-response" claim and call it what it is: a decision log.

---

## 3. Dead weight — code that never executes here

| Item | Evidence | Size | Action |
|---|---|---|---|
| `scripts/context-monitor.py` | Zero references anywhere in the repo (no statusLine key, no hook, no doc) ✅ | 298 | **Delete** |
| `scripts/check_plan_format.py` + test | Only caller is its own pytest suite — CI tests a validator that never validates anything; carries a speculative `PLAN_MAX_FILES_PER_TASK` env flag nobody sees | 198 + 242 | **Wire into `render-plan-on-write.sh`/CI (~3 lines) or delete** |
| `commit-quality-gate.sh` checks 2/2.5/3 | All target `app/**/*.py`; no `app/` directory exists ✅ — ~110 of 181 lines can never fire, yet run on every commit | ~110 + 137 test | **Keep the secrets scan (~45 lines); move app checks to `templates/stacks/`** |
| `hooks/protected-path-guard.sh` (dormant) | Never wired "by design" — wiring it is itself Rule-4; duplicates risk-corroboration's `high-blast` category | 50 + tests | **Delete** |
| `hooks/auto-test-on-change.sh` (dormant) | 3-ecosystem detection + custom-override generality in a hook that isn't wired | 120 + tests | **Wire it or strip to pytest-only** |
| `templates/TEST_MATRIX.template.md` | 0 instances across 33 specs despite an orchestration.md mandate; nothing reads it | 34 + prose | **Delete template + mandate** |
| `templates/stacks/{nextjs,node,django}` | Landed in one commit, never edited, never consumed | ~640 | **Cut unless the harness is genuinely for distribution** |
| `scripts/check_lane_evidence.py` | Called "single source of truth" by rules but has no automated caller; duplicates verify_summary.py's parser, kept in sync *by comment* | 223 + 190 | **Merge into `verify_summary.py --lane`; wire into commit gate** |
| `REQ.md`, `agent-memory/`, `agents/PROJECT.md` | REQ.md stale stub (typo'd title, no live refs); agent-memory has only a README; agents/PROJECT.md is byte-identical to its template — never rendered for this repo | ~110 | **Delete / fold / fill** |
| `PR_TEMPLATE.md` | Currently holds a *specific* PR's body (compound-ddr), not a template — a scratch file wearing a template's name; polluting git status right now ✅ | 28 | **Investigate; have create-pr write to an untracked path** |

---

## 4. Duplication of truth — the structural problem

The same facts live in many places, and an 800+-line linter suite exists to hold the copies together:

- **Hard-gate list: 6 places** (harness-manifest.json, risk-corroboration.sh source, auto-correct-scope.md Rule 4, HARNESS.md §5, feature-intake SKILL.md, orchestration.md).
- **Lane semantics: 7 places.** **Hook wiring table: 4 places.** **Workflow-chain diagram: 4 copies.**
- **Branch-isolation rule: restated near-verbatim in 5+ skill locations** plus rules/ and CLAUDE.md — while `branch-isolation-guard.sh` already enforces it mechanically.
- `check_manifest.py:83–104` **regex-parses bash source** to prove the hook matches the manifest — a meta-check that exists only because the vocabulary lives in 4 places. If `risk-corroboration.sh` read the manifest directly (jq, ~10 lines), that whole section dies.
- `skills/compound/SKILL.md` embeds ~180 lines of templates **byte-duplicated** from `skills/compound/templates/*.md`, which it never references (0 grep hits ✅).

`lint-doc-truth.sh` demonstrably earned its keep (two prior drift-repair PRs) — but it is a *symptom*: it lints duplication into consistency instead of deleting the duplication. **Fix pattern: one canonical home per fact** (manifest for gates, settings.json for hooks — generate the CLAUDE.md table from it, auto-correct-scope.md for lanes, plan-format.md for the task schema); everything else becomes a pointer.

---

## 5. Ceremony vs. scale

### The review-oracle stack — MEDIUM-HIGH
~12 distinct LLM review mechanisms + ~9 mechanized gates exist. A normal-lane 3-task change passes through **~9 LLM review passes + ~8 hook/script gates ≈ 17 checks**. Meanwhile the one critical-severity solutions entry (`unverified-premise-propagates-through-plan-anchored-reviews`) proves the stack shares blind spots — all three oracles inherited the same false premise. More oracles ≠ independent oracles.
**Fix:** scale the chain by lane. Normal lane → 1–2 correctness angles + intent-review only when intake confidence < high; the full 6-angle + scorer stack reserved for high-risk. (correctness-review's internal design is benchmark-backed — keep it; gate its *invocation*.)

### Per-call hook overhead — MEDIUM
Every Bash call (even `ls`) spawns 4 PreToolUse processes, 3 of which are commit-only, each with a duplicated ~15-line prologue. Every Edit/Write spawns 4. An actual `git commit` runs ~6 `git diff`s + ~12 greps across the 4 gates. `branch-guard.sh` is subsumed by `branch-isolation-guard.sh`'s write-time deny — the only commits it can still catch are the deliberately-exempt specs/ bookkeeping ones, so its warnings are mostly noise.
**Fix:** merge the commit gates behind one dispatcher (4 spawns → 2 per Bash call); delete branch-guard.

### Config-surface sprawl — MEDIUM
11 env vars / escape hatches (HARNESS_SHARED_BRANCHES, BRANCH_ISOLATION_REASON, PROTECTED_PATH_REASON, RISK_CORROBORATION_STRICT, RISK_WARN_CATEGORIES, REQUIRE_VERIFY, BLAST_RADIUS_STRICT, AUTO_TEST_CMD, AUTO_TEST_PATTERN, SESSION_KNOWLEDGE_DIR, + FULL_ARTIFACTS in rules). Three strict-mode toggles default off with no evidence of ever being set; two belong to a dormant hook. `risk-corroboration.sh:47–64`'s `category_mode()` is an 18-line case statement where **every branch returns "block"** — a constant wearing a function costume, plus a `RISK_WARN_CATEGORIES` parser for a "Phase 7 loosening" that never happened.
**Fix:** cutting the findings above removes 5 of 11 vars; delete `category_mode()`.

### Always-on context tax — HIGH
`rules/architecture.md` (40 lines) self-declares "does not apply here"; `rules/guidelines.md` (45 lines) is an unfilled per-stack placeholder ("Coverage target: fill per stack") — both auto-loaded into **every session**. `specs/STATE.md`: 65/65 session breadcrumbs record `user_turns: 0` ✅ — the field has never held a nonzero value; ~420 of 482 lines are noise, and it references a `/session-tracker` that doesn't exist.
**Fix:** shrink both rules files to ~5-line pointers; fix or drop the breadcrumb fields that never populate.

### Rollback theater — MEDIUM
15/33 SUMMARYs contain the literal unedited `git revert <sha>` placeholder — not re-runnable, contradicting "evidence over assertion"; the checker accepts it as "non-empty."
**Fix:** template default `- none`; checker rejects `<sha>`.

---

## 6. What is genuinely good (verified — do not cut)

- **`rules/behavior.md`** — dense, universal; the best file in the repo.
- **SUMMARY.md core contract** — Lane/Confidence/Reason/Verify/Intent are all machine-read (risk-corroboration, check_lane_evidence, verify_summary, intent-review) and filled with real values in 33/33 specs.
- **`hooks/lib/git-command.sh`** — real bypass fix, honest known-uncaught list, mutation-tested. **`check-untracked-py.sh`**, **`branch-isolation-guard.sh`**, **`ruff-on-edit.sh`**, **`render-plan-on-write.sh`** — small, load-bearing.
- **`verify_summary.py`** — the one gate with real teeth (parse + re-run + trivial-command denylist); its 403-line test suite is justified.
- **correctness-review's SCORE/threshold design** — benchmark-backed (`benchmarks/review-chain`) with a documented rejected alternative. **intent-review's plan-blindness** — cheap, closes a real Goodhart gap.
- **`/compound` + doc-truth lint + `harness-manifest.json`** — the compounding loop demonstrably works (INDEX auto-gen, `confirmed_at` staleness); the manifest is the one duplication-killer done right.
- **The test suite** (~2,285 lines guarding hooks/scripts, hermetic, mutation-tested) and the **lane/confidence design principle** (ceremony scales with risk; the human gate scales with ambiguity) — this is the 20% to build the minimal version around.
- **Honesty culture** — the failure log's self-critical entries are exactly right; the problem is only that the harness hasn't consumed its own findings (C4).

---

## 7. Prioritized action plan

**Phase 1 — correctness fixes (small diffs, high value):**
1. C1: writing-plans → point at plan-format.md (kills the format contradiction).
2. C2: brainstorming → drop the "every project" hard-gate.
3. C4: `:!tests/` in risk-corroboration pathspec (apply your own failure memo).
4. C3: `branches: [v2]` → `[main]` (or retire the pipeline).
5. C5: enforce or demote the ESCALATIONS "deny" claim.

**Phase 2 — delete dead weight (~1,700 lines, zero enforcement loss):**
context-monitor.py · check_plan_format.py+test (or wire it) · protected-path-guard+tests · branch-guard · TEST_MATRIX template+mandate · commit-quality-gate app/ checks → stacks template · category_mode/RISK_WARN_CATEGORIES · REQ.md · speculative stack profiles · harness-audit check #4 (25 stale findings = alarm fatigue) · deploy-harness spinner + backup-policy branch.

**Phase 3 — deduplicate truth (~700+ lines of prose, plus less linter surface):**
compound inline templates → file refs (~180) · branch-rule prose → one-line pointers (~60+) · hook table generated from settings.json · risk-corroboration reads manifest directly → delete check_manifest §B · merge check_lane_evidence into verify_summary · merge executing-plans into subagent-driven-development (~100 net) · trim s-d-d's graph/example/advantages (~170) · shrink architecture.md/guidelines.md to pointers.

**Phase 4 — scale ceremony by lane:**
Normal lane: 1–2 correctness angles, no per-finding scorer, intent-review only at confidence < high. Full stack = high-risk only. Merge commit gates behind one dispatcher. Fix STATE.md breadcrumb noise.

**Net effect:** ~60% cut in always-on context (~13k → ~5k tokens/session), 9 LLM reviews → 2–3 for normal lane, 7 bookkeeping surfaces → ~2, ~3,500–4,000 fewer lines — while every currently-*enforced* behavior survives.

---

## Appendix A — per-skill verdicts (skills agent)

| Skill | Lines | Verdict | Reason |
|---|---|---|---|
| skills/README.md | 351 | trim | rationale sections duplicate skill docs; keep the handoff map |
| feature-intake | 212 | trim | unused `Input-type:` field; dedupe branch-rule prose |
| brainstorming | 171 | trim | delete "everything needs design" gate (C2) |
| xia2 | 240 | keep | classifier is load-bearing; its ~300-line manual "tests" need a runner or a cut |
| bootstrap-xia2 | 370 | trim | cut example-output blocks + unexercised stack heuristics (~70) |
| writing-plans | 209 | **fix + trim** | conflicting task format (C1) |
| visual-planner | 222 | keep | parsing contracts, deterministic by design |
| using-git-worktrees | 314 | trim ~90 | superpowers global-dir flow + triple restatement; keep the deploy-harness step (Skill-tool breakage is real) |
| subagent-driven-development | 437 | trim ~170 | dot graph, example workflow, advantages = restatements |
| executing-plans | 126 | merge into s-d-d | same gates; only dispatch differs |
| correctness-review | 161 | keep | benchmark-justified; gate invocation by lane |
| intent-review | 149 | keep, light trim | mechanism sound |
| review-diff | 62 | keep | small, optional |
| create-pr | 88 | keep | fix output path (writes PR_TEMPLATE.md into git status) |
| finishing-a-development-branch | 150 | keep | lifecycle/hook contracts live here |
| compound | 480 | trim ~200 | inline templates byte-duplicate templates/ dir (0 refs) |

## Appendix B — per-hook verdicts (hooks agent)

| Hook | Lines | Wired | Verdict | Reason |
|---|---|---|---|---|
| check-untracked-py | 26 | ✅ | keep | encodes real CI-break lesson |
| commit-quality-gate | 181 | ✅ | **trim** | keep secrets scan; app/ checks dead here |
| risk-corroboration | 157 | ✅ | **trim** | fix tests/ FP (C4); delete category_mode |
| branch-guard | 30 | ✅ | **delete** | subsumed by branch-isolation-guard |
| branch-isolation-guard | 61 | ✅ | keep | closes a real structural gap |
| ruff-on-edit | 12 | ✅ | keep | minimal, correct |
| blast-radius-check | 72 | ✅ | keep | silent without an active plan |
| render-plan-on-write | 36 | ✅ | keep | deterministic, non-blocking |
| scope-gate | 22 | ✅ | keep (borderline) | cheap, advisory |
| state-breadcrumb | 107 | ✅ | trim | over-defensive for a never-blocks appender; fields never populate |
| session-knowledge | 103 | ✅ | trim | dual empty-format parsing over-built |
| auto-test-on-change | 120 | ⬜ | **wire or strip** | speculative generality, unwired |
| protected-path-guard | 50 | ⬜ | **delete** | dormant forever by design; duplicate gate |
| lib/git-command.sh | 96 | shared | keep | load-bearing, mutation-tested |

## Appendix C — per-script verdicts (scripts agent)

| Script | Lines | Called by | Verdict | Reason |
|---|---|---|---|---|
| context-monitor.py | 298 | nothing | **DELETE** | zero refs ✅ |
| check_plan_format.py (+test) | 198+242 | own pytest only | **WIRE or DELETE** | validator with no enforcement point |
| check_lane_evidence.py (+test) | 223+190 | manual only | **MERGE into verify_summary** | duplicate parser synced by comment |
| check_manifest.py | 154 | CI, harness-audit, feature-intake | keep, shrink §B | drop regex-on-bash; hook reads manifest |
| verify_summary.py (+test) | 357+403 | commit-gate (opt-in), ci-strict-gate | keep | real teeth; consider dropping unused write-mode |
| ci-strict-gate.sh | 86 | harness-ci | keep | proportionate |
| lint-doc-truth.sh | 89 | CI | keep | earned (2 drift-repair PRs) |
| harness-audit.sh | 236 | bookkeeping, harness-status | trim check #4 | 25 stale findings = alarm fatigue |
| check-contract-impact.sh | 60 | harness-audit | keep (marginal) | fold-in candidate |
| bookkeeping.sh | 119 | post-merge workflow (**inert**) | fix wiring or retire | dead since v2→main (C3) ✅ |
| harness-status.sh | 103 | manual | keep | cheap dashboard |
| deploy-harness.sh | 397 | install, README | keep, trim −70 | spinner + backup-policy sprawl |
| install-harness.sh | 249 | curl one-liner | keep | split from deploy is sound |
| run-tests.sh | 53 | CI + devs | keep | thin, correct |

## Appendix D — rules/templates/governance verdicts (process agent)

| File | Lines | Consumed by | Verdict | Reason |
|---|---|---|---|---|
| rules/behavior.md | 58 | every session | **keep** | dense, universal |
| rules/plan-format.md | 132 | render_plan.py, hooks | **keep** | machine contract |
| rules/orchestration.md | 121 | prose readers | trim | policies restated 3×; TEST_MATRIX ref dead |
| rules/auto-correct-scope.md | 106 | manifest/hook, agents | keep, trim Rule-4 dup | the real autonomy contract |
| rules/wave-parallelism.md | 56 | 14 plans | merge into plan-format | real but doesn't need its own file |
| rules/architecture.md | 40 | session context | shrink to ~5 lines | self-declared "does not apply here" |
| rules/guidelines.md | 45 | session context | shrink to ~5 lines | unfilled placeholder, loaded every session |
| templates/SUMMARY.template.md | 85 | 4 machine consumers | **keep**; fix Rollback default | most machine-read template |
| templates/TEST_MATRIX.template.md | 34 | nothing (0/33 specs) | **delete** | pure speculation |
| templates/ESCALATIONS.template.md | 28 | 4 uses, 0 enforcement | keep as log; enforce or drop "deny" claim | gate is fiction (C5) |
| templates/stacks/fastapi + _skeleton | ~420 | bootstrap-xia2 | keep | the actually-used profile |
| templates/stacks/{nextjs,node,django} | ~640 | never consumed | cut unless distributing | one-commit speculative breadth |
| agents/{coding,reviewer,test-runner}.md | 187 | registered agent types | keep | wired, distinct roles |
| agents/PROJECT.md | 67 | coding/test-runner | fill or delete | byte-identical to template |
| CLAUDE.md | 93 | every session | keep; generate hook table | table dupes settings.json; "app/" gotcha targets nonexistent dir |
| HARNESS.md | 73 | humans | trim/merge into README | 4th restatement of lanes/gates/chain |
| REQ.md | 22 | nothing live | delete/fold | stale stub |
| harness-manifest.json | 111 | check_manifest, contract-impact | keep | duplication-killer done right |
