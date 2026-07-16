---
slug: harness-comparison-adoptions
status: proposed
owner: Minh Tran
created: 2026-06-12
---

# Harness Comparison Adoptions — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use subagent-driven-development (same session) or
> executing-plans (parallel session) to implement this plan task-by-task — **after the user
> selects which tracks to run.**

**Goal:** Implement the adoption ideas from `docs/research-claude-code-harness-comparison.md`
(comparison against Chachamaru127/claude-code-harness), packaged as 9 independent tracks so
the user can greenlight any subset.

**Architecture:** Each track maps to one idea from the report §4. Tracks are decoupled —
selecting any subset yields working, testable changes. Two file-overlap chains force ordering
when both members are selected: Track 1 → Track 2 (both edit the reviewer prompt files) and
Track 3 → Track 4 (both edit `rules/plan-format.md`). Wave numbers below assume **all** tracks
are selected; after selection, drop unselected tasks and renumber waves keeping relative order.

**Tech Stack:** Markdown skills/rules, bash hooks + `tests/hooks/*.test.sh` contract tests,
Python (`scripts/check_plan_format.py` + pytest), existing `scripts/run-tests.sh` CI suite.

---

## 1. Motivation

The research report found our weakest spots are exactly where claude-code-harness is
strongest: enforcement lives in prompts instead of structure, "done" is prose instead of
validators, protected paths are a STOP-list instead of a hook, and we have **zero empirical
evidence** the review chain catches anything. Each track closes one of those gaps with the
smallest credible version.

## 2. Non-goals

- No multi-tool mirrors (Codex/OpenCode/Cursor) — we target Claude Code only.
- No approval-gated-everything loop — the lane/confidence autonomy model stays.
- No out-of-process memory daemon — `docs/solutions/` + `agent-memory/` stay file-based.
- No automated benchmark runner in v1 (Track 7 is a manual protocol; automation later if the
  manual loop proves valuable).
- Tracks 8 and 9 get **kickoff design docs only** here — each is a larger bet that needs its
  own spec + PLAN before any code (per report §4 "worth a spec each").

## 3. Decision Matrix (pick tracks here)

| Track | Idea (report §4) | Lane | Effort | Value | Conflicts / depends | Tasks |
|---|---|---|---|---|---|---|
| **1** | Read-only review agents (`disallowedTools` → tools whitelist) | normal | ~½ day | High — structural review independence | Track 2 edits same prompt files (run 1 before 2) | 1.1–1.2 |
| **2** | `not_observed != absent` named rule | tiny | ~1 h | Medium-high — greppable epistemic rule at every review layer | after Track 1 if both selected | 2.1–2.2 |
| **3** | Commit sha per completed task in Status Log | tiny | ~2 h | Medium — plan table becomes a ledger | Track 4 edits same rule files (run 3 before 4) | 3.1–3.2 |
| **4** | Machine-checkable DoD in `<done>` | normal | ~½ day | Medium — "done" becomes re-runnable | after Track 3 if both selected; renderer change = Rule-4 STOP | 4.1–4.2 |
| **5** | Break-glass protected-paths hook | **high-risk** | ~1 day | High — Rule-4 STOP list becomes machine-enforced | settings.json registration needs human confirm | 5.1–5.2 |
| **6** | Integration evidence-tier table | tiny | ~1 h | Medium — kills silent doc rot | none | 6.1 |
| **7** | Review-chain micro-benchmark (manual v1) | normal | ~1–2 days | **Highest** — first real catch-rate number | none | 7.1–7.3 |
| **8** | Consolidated gate dispatcher (kickoff only) | tiny (design doc) | ~½ day | High later — full work needs own PLAN | Track 9 shares the SQLite store decision | 8.1 |
| **9** | Session/state ledger (kickoff only) | tiny (design doc) | ~½ day | High later — full work needs own PLAN | design must align with Track 8 | 9.1 |

## 4. Success Criteria

- Every selected track's `<verify>` commands exit 0, and `bash scripts/run-tests.sh` stays green.
- Track 1: dispatching either review skill uses an agent type whose tool whitelist excludes Write/Edit/Agent.
- Track 5: a write to `settings.json` or `hooks/*.sh` without `BREAK_GLASS_REASON` is blocked by hook, with a contract test proving it.
- Track 7: a baseline results file exists with a measured catch rate over 5 fixtures.
- Tracks 8/9: a `design.md` exists that a future `/writing-plans` run can consume directly.

---

## 5. Tasks

### Track 1 — Structurally read-only review agents (idea 1)

#### Task 1.1 — Create the read-only `reviewer` agent definition

```xml
<task id="1.1" wave="1">
  <files>agents/reviewer.md</files>
  <action>Create agents/reviewer.md following the frontmatter shape of agents/test-runner.md (name, description, tools, model, memory). Set `name: reviewer`; `tools: Glob, Grep, Read, Bash` — deliberately NO Write, NO Edit, NO Agent (structural review independence: the reviewer cannot modify files or spawn nested agents; Bash stays for `git diff`/`git log`/running tests read-only). Omit `model:` (callers pass their own per the ensemble-diversity rule in the reviewer prompts). Body: a short role statement — "You produce findings; you never fix. Your final message is the deliverable." plus a note that any urge to edit a file is itself a finding to report. Acknowledged limitation: Bash remains mutation-capable — the body's "never fix" instruction is the only guard on that channel; the structural guarantee covers Write/Edit/Agent. Keep it under ~40 lines; mirror the tone of agents/test-runner.md.</action>
  <verify>grep -q '^name: reviewer$' agents/reviewer.md && grep -q '^tools: Glob, Grep, Read, Bash$' agents/reviewer.md && ! grep -qE '^tools:.*(Write|Edit)' agents/reviewer.md</verify>
  <done>agents/reviewer.md exists with a tools whitelist excluding Write/Edit/Agent and no model pin.</done>
</task>
```

#### Task 1.2 — Dispatch the three review passes with `subagent_type: reviewer`

```xml
<task id="1.2" wave="2">
  <files>skills/correctness-review/correctness-reviewer-prompt.md, skills/correctness-review/correctness-scorer-prompt.md, skills/intent-review/intent-reviewer-prompt.md</files>
  <action>In each of the three prompt files, find the single fenced `Task tool` dispatch block (headed `Task tool (general-purpose):`; it contains a `model:` line — `<different from implementer; ...>` in the two reviewer prompts ~line 25, `<cheap/fast model ...>` in the scorer prompt ~line 23). In each block: update the header to name the reviewer agent type (e.g. `Task tool (reviewer):`) and add `subagent_type: reviewer`, with one explanatory sentence: "reviewer is a read-only agent (no Write/Edit/Agent) — review independence is enforced structurally, not by instruction." Do not change the model lines, other dispatch parameters, or the finding rubrics.</action>
  <verify>grep -q 'subagent_type: reviewer' skills/correctness-review/correctness-reviewer-prompt.md && grep -q 'subagent_type: reviewer' skills/correctness-review/correctness-scorer-prompt.md && grep -q 'subagent_type: reviewer' skills/intent-review/intent-reviewer-prompt.md</verify>
  <done>All three review-pass dispatches name the read-only reviewer agent type.</done>
</task>
```

### Track 2 — `not_observed != absent` as a named rule (idea 3 of "learn")

#### Task 2.1 — Add the rule to behavior guidelines (both copies)

```xml
<task id="2.1" wave="1">
  <files>rules/behavior.md, .claude/rules/behavior.md</files>
  <action>Add one bullet to section "## 1. Think Before Coding" in rules/behavior.md: "- `not_observed != absent` — a missing search result, an unread file, or unavailable memory means *unknown*, not *absent*. Before claiming something does not exist, state where you looked." Apply the identical edit to .claude/rules/behavior.md (the two copies must stay byte-identical — CLAUDE.md names rules/behavior.md as the single source of truth and the doc-truth lint may compare them).</action>
  <verify>grep -q 'not_observed != absent' rules/behavior.md && diff -q rules/behavior.md .claude/rules/behavior.md</verify>
  <done>The named epistemic rule appears in §1 of both behavior.md copies and the copies are identical.</done>
</task>
```

#### Task 2.2 — Enforce the rule inside the two review prompts

```xml
<task id="2.2" wave="3">
  <files>skills/correctness-review/correctness-reviewer-prompt.md, skills/intent-review/intent-reviewer-prompt.md</files>
  <action>In each reviewer prompt's finding-requirements section, add a requirement named `not_observed != absent`: any finding (or all-clear claim) that asserts absence — "no callers", "no test covers this", "nothing handles X", "no gap found" — MUST name the locations searched (paths/globs/commands). A claim that cannot cite its search surface is reported as `unknown`, never as absent. Wave 3 because Track 1.2 touches the same files — if Track 1 is not selected, this task moves to wave 1.</action>
  <verify>grep -q 'not_observed != absent' skills/correctness-review/correctness-reviewer-prompt.md && grep -q 'not_observed != absent' skills/intent-review/intent-reviewer-prompt.md</verify>
  <done>Both reviewer prompts require absence-claims to cite their search surface or downgrade to unknown.</done>
</task>
```

### Track 3 — Commit sha per completed task (idea: plan table as ledger)

#### Task 3.1 — Make the sha a Status Log invariant in the rules

```xml
<task id="3.1" wave="1">
  <files>rules/plan-format.md, .claude/rules/plan-format.md, rules/wave-parallelism.md, .claude/rules/wave-parallelism.md</files>
  <action>In plan-format.md "## PLAN.md structure" add a Status Log line-format convention: a task may only be marked done as `&lt;task-id&gt; — done — &lt;commit-sha&gt;` (short sha mandatory; one line per task). In wave-parallelism.md "## Collection protocol" step 2, strengthen "Append task commit shas" to state the per-task invariant: a Status Log entry without a sha does not count as done. Keep rules/ and .claude/rules/ copies byte-identical for both files.</action>
  <verify>grep -q 'done — &lt;commit-sha&gt;\|done — <commit-sha>' rules/plan-format.md && diff -q rules/plan-format.md .claude/rules/plan-format.md && diff -q rules/wave-parallelism.md .claude/rules/wave-parallelism.md</verify>
  <done>Both rule files (both copies) state the sha-per-done-task invariant.</done>
</task>
```

#### Task 3.2 — Lint it: warn on done-entries missing a sha

```xml
<task id="3.2" wave="2">
  <files>scripts/check_plan_format.py, scripts/test_check_plan_format.py</files>
  <action>TDD. First add tests to scripts/test_check_plan_format.py: (a) a PLAN.md whose Status Log marks a task done WITH a 7–40 char hex sha → no warning; (b) marks done WITHOUT a sha → a warning naming the task id; (c) warnings do NOT fail the check (exit 0) — existing plans must stay green (warn-only rollout, mirroring the R14 advisory-first pattern from the research report). Run pytest, watch the new tests fail. Then implement in scripts/check_plan_format.py: scan Status Log entries that reference a valid task id with a done-marker (done/✅/completed) and emit `WARN: task &lt;id&gt; marked done without commit sha` when no hex sha (7-40 chars) is present on the line. Reuse the existing status-log parsing approach (see _done_task_ids in .claude/skills/visual-planner/render_plan.py for the reference regex, but implement locally — do not import from the renderer).</action>
  <verify>python3 -m pytest scripts/test_check_plan_format.py -q</verify>
  <done>check_plan_format.py warns (exit 0) on sha-less done entries; pytest green including 3 new tests.</done>
</task>
```

### Track 4 — Machine-checkable DoD in `<done>` (idea 4)

#### Task 4.1 — Extend the `<done>` convention in plan-format.md

```xml
<task id="4.1" wave="2">
  <files>rules/plan-format.md, .claude/rules/plan-format.md</files>
  <action>In plan-format.md XML Schema section, extend the `<done>` description: `<done>` MAY be a lettered validator checklist — each item `(a)`, `(b)`, ... is a machine-checkable condition (a grep hit, a test that passes, a schema check), with at most one trailing prose summary line. Add a short example: "(a) agents/reviewer.md contains 'tools:' excluding Write — grep 0 hits for 'Write' on that line; (b) python3 -m pytest scripts/test_check_plan_format.py -q PASS". State the intent: done-ness becomes re-runnable by a hook instead of judged by an agent. Wave 2 because Track 3.1 edits the same files; if Track 3 is not selected this moves to wave 1. Keep both copies identical. Do NOT change check_plan_format.py validation (multi-line done is already legal) and do NOT touch the renderer in this task.</action>
  <verify>grep -q 'lettered validator' rules/plan-format.md && diff -q rules/plan-format.md .claude/rules/plan-format.md</verify>
  <done>plan-format.md (both copies) documents the lettered-validator form of done with an example.</done>
</task>
```

#### Task 4.2 — Prove the renderer survives checklist-style `<done>`

```xml
<task id="4.2" wave="3">
  <files>tests/scripts/render-done-checklist.test.sh</files>
  <action>Add a contract test following the existing tests/scripts/*.test.sh pattern (source tests/lib.sh): build a temp spec dir with a minimal PLAN.md whose single task has a 3-item lettered `<done>` checklist, run .claude/skills/visual-planner/render_plan.py against it (check the script's CLI usage first — it is invoked by hooks/render-plan-on-write.sh, read that hook for the exact call shape), and assert the produced PLAN.html contains all three markers (a)/(b)/(c) and the script's self-check passes. HARD CONSTRAINT: if the renderer flattens or drops checklist items, do NOT modify render_plan.py — it is a Rule-4 high-blast file; record the failure in the test as expected-fail, report it in SUMMARY ### Deviations, and escalate per rules/auto-correct-scope.md.</action>
  <verify>bash tests/scripts/render-done-checklist.test.sh</verify>
  <done>Contract test proves (or explicitly documents the escalated failure of) checklist-done rendering; render_plan.py untouched.</done>
</task>
```

### Track 5 — Break-glass protected-paths hook (idea 5) — HIGH-RISK

> Hard gate: registers a new always-on hook and edits `settings.json` (both on the Rule-4
> high-blast list). Task 5.2 requires explicit human confirmation before execution.

#### Task 5.1 — Hook script + contract test (no registration yet)

```xml
<task id="5.1" wave="1">
  <files>hooks/protected-paths.sh, tests/hooks/protected-paths.test.sh, .gitignore</files>
  <action>TDD: write tests/hooks/protected-paths.test.sh first, following the harness pattern of tests/hooks/branch-guard.test.sh (source tests/lib.sh; feed the hook PreToolUse-style JSON on stdin). Cases: (1) Edit targeting settings.json → blocked (exit 2 / deny per the convention used by check-untracked-py.sh — read it first and match the blocking convention exactly); (2) Write targeting hooks/commit-quality-gate.sh → blocked; (3) Edit targeting .claude/skills/visual-planner/render_plan.py → blocked; (4) same as (1) but with BREAK_GLASS_REASON="hotfix-issue-123" in env → allowed AND a line "&lt;ISO-date&gt; &lt;path&gt; &lt;reason&gt;" appended to specs/.break-glass.log (the override becomes an audit record); (5) BREAK_GLASS_REASON set but empty → still blocked; (6) Edit to an ordinary file (e.g. docs/x.md) → allowed, silent. Then implement hooks/protected-paths.sh: protected list = settings.json, hooks/*.sh, .claude/skills/visual-planner/render_plan.py (the Rule-4 high-blast set from rules/auto-correct-scope.md); fail-open on malformed input (never block when the payload cannot be parsed — mirror existing hooks' defensive style). Add `specs/.break-glass.log` to .gitignore — it is a local audit artifact, like PLAN.html; tracking it would dirty the tree on every override.</action>
  <verify>bash tests/hooks/protected-paths.test.sh</verify>
  <done>Hook blocks high-blast writes, allows them only with a non-empty logged reason, fails open on garbage input; contract test green. Not yet registered — dormant.</done>
</task>
```

#### Task 5.2 — Register the hook (HUMAN CONFIRM REQUIRED)

```xml
<task id="5.2" wave="2">
  <files>settings.json, CLAUDE.md</files>
  <action>STOP — present the diff of this task to the human before applying (hard gate: settings.json is high-blast; rules/auto-correct-scope.md Rule 4). On approval: register hooks/protected-paths.sh in settings.json under PreToolUse with an Edit|Write matcher (mirror the registration shape of the existing PostToolUse Edit/Write hooks; note the repo-root settings.json is the shared config — do NOT touch .claude/settings.json or settings.local.json). Then add a row to the CLAUDE.md "## Hooks" table (trigger: PreToolUse (Edit/Write); action: block writes to high-blast paths unless BREAK_GLASS_REASON is set — logged to specs/.break-glass.log; Wired ✅) — the doc-truth lint fails if the table contradicts settings.json. Record rollback in SUMMARY.md ### Rollback: git revert of this commit de-registers the hook.</action>
  <verify>bash scripts/lint-doc-truth.sh && grep -q 'protected-paths.sh' settings.json && grep -q 'protected-paths.sh' CLAUDE.md</verify>
  <done>Hook is wired in settings.json, CLAUDE.md table matches, doc-truth lint green, rollback recorded — all post human approval.</done>
</task>
```

### Track 6 — Integration evidence-tier table (idea 6)

#### Task 6.1 — Add the tier table + graduation rule to skills/README.md

```xml
<task id="6.1" wave="1">
  <files>skills/README.md</files>
  <action>Add a section "## Integration Evidence Tiers" after "## External Skills": a table with columns Integration | Kind | Tier | Evidence. Rows: each external skill referenced by workflows (systematic-debugging, test-driven-development, requesting-code-review, session-tracker, skill-creator), each MCP dependency (code-review-graph, context7), and the cross-skill handoff edges from the Handoff Map that have actually been exercised (at minimum: subagent-driven-development → correctness-review → intent-review, exercised in the intent-review dogfood — cite commit a2a4349). Tiers: ci-proven (a CI job runs it) / manually-verified (date) (a recorded run exists) / documented-only (never observed here). Close with the graduation rule, quoting the research report: an edge only moves UP a tier when a recorded run exists in this repo — support claims are never inherited (`not_observed != absent`). Be honest: most external-skill rows start at documented-only.</action>
  <verify>grep -q 'Integration Evidence Tiers' skills/README.md && grep -q 'documented-only' skills/README.md && bash scripts/lint-doc-truth.sh</verify>
  <done>skills/README.md carries an honest tier table with the graduation rule; doc-truth lint green.</done>
</task>
```

### Track 7 — Review-chain micro-benchmark, manual v1 (idea 7 — the big one)

#### Task 7.1 — Scaffold the benchmark directory + protocol

```xml
<task id="7.1" wave="1">
  <files>benchmarks/review-chain/README.md, benchmarks/review-chain/results/template.md</files>
  <action>Create benchmarks/review-chain/README.md defining the manual v1 protocol: (1) each fixture under fixtures/&lt;name&gt;/ contains intent.md (a verbatim-style user request), diff.patch (a small self-contained diff implementing it with ONE planted defect), and truth.md (the ground-truth finding: defect class, location, and whether /correctness-review or /intent-review should catch it); (2) a run = applying the fixture in a scratch worktree, executing /correctness-review then /intent-review standalone, and scoring each against truth.md as caught / missed / false-positive, recording token cost per pass; (3) results land in results/&lt;date&gt;-&lt;label&gt;.md using results/template.md (columns: fixture, defect class, expected oracle, caught-by, verdict, tokens). State the claim-discipline rule up front, borrowed from the breezing-bench design: the benchmark measures ONLY whether the two review skills catch the planted defect classes — it is not evidence about the full chain. Note: automated runner is explicitly out of scope for v1.</action>
  <verify>test -f benchmarks/review-chain/README.md && test -f benchmarks/review-chain/results/template.md && grep -q 'caught / missed / false-positive' benchmarks/review-chain/README.md</verify>
  <done>Protocol + results template exist; scope and claim limits are stated in the README.</done>
</task>
```

#### Task 7.2 — Author 5 seeded fixtures

```xml
<task id="7.2" wave="2">
  <files>benchmarks/review-chain/fixtures/none-deref/, benchmarks/review-chain/fixtures/missing-await/, benchmarks/review-chain/fixtures/soft-delete-filter/, benchmarks/review-chain/fixtures/excess-scope/, benchmarks/review-chain/fixtures/intent-gap/</files>
  <action>Author 5 fixtures per the 7.1 format, each a small (≤80-line) FastAPI-style diff consistent with .claude/rules/architecture.md conventions. Three correctness-oracle fixtures: none-deref (Optional return used without guard), missing-await (async repo call not awaited — passes type checks, fails at runtime), soft-delete-filter (query missing deleted_at IS NULL — the rules/guidelines.md checklist item). Two intent-oracle fixtures: excess-scope (diff implements the request PLUS an unrequested refactor of an adjacent function), intent-gap (request asks for validation on two endpoints, diff covers one). Each truth.md states the single planted defect, its exact location, the expected catching oracle, and what a false-positive would look like. Defects must be realistic — copied from the bug classes /correctness-review already names (None/async/DB) — not contrived puzzles.</action>
  <verify>test "$(ls -d benchmarks/review-chain/fixtures/*/ | wc -l | tr -d ' ')" = "5" && test "$(ls benchmarks/review-chain/fixtures/*/truth.md | wc -l | tr -d ' ')" = "5"</verify>
  <done>5 fixtures exist, each with intent.md + diff.patch + truth.md and exactly one planted defect.</done>
</task>
```

#### Task 7.3 — Baseline run + first catch-rate number

```xml
<task id="7.3" wave="3">
  <files>benchmarks/review-chain/results/2026-06-baseline.md</files>
  <action>Execute the 7.1 protocol once over all 5 fixtures (scratch worktree per fixture; /correctness-review then /intent-review; score vs truth.md). Record per-fixture rows plus the headline numbers: catch rate (n/5), false positives, and approximate token cost per pass (from session usage). Honesty rules from the protocol apply: report misses plainly; do not re-run a fixture until it passes; if a skill catches the defect for the wrong reason, score it caught-wrong-reason and say so. This file is the repo's first empirical claim about the review chain — it is also the regression baseline for any future edit to the two review skills.</action>
  <verify>test -f benchmarks/review-chain/results/2026-06-baseline.md && grep -qi 'catch rate' benchmarks/review-chain/results/2026-06-baseline.md</verify>
  <done>Baseline results file exists with per-fixture verdicts and a headline catch rate.</done>
</task>
```

### Track 8 — Consolidated gate dispatcher (idea 8) — kickoff only

#### Task 8.1 — Design doc for the dispatcher (no code)

```xml
<task id="8.1" wave="1">
  <files>specs/gate-dispatcher/design.md</files>
  <action>Write the design document (no implementation) for consolidating the four commit-time hooks (commit-quality-gate.sh, risk-corroboration.sh, branch-guard.sh, check-untracked-py.sh) behind one dispatcher, adapting the claude-code-harness model (docs/research-claude-code-harness-comparison.md §1.1): single entrypoint registered once in settings.json; declarative ordered rule table, first-match-wins; each rule a pure check function returning block/warn/pass + reason; fail-open with per-rule timeout; every decision appended to a ledger (file-based JSONL first — SQLite only if Track 9 lands). MUST address: language choice (bash thin-shim vs Python — recommend one with rationale), migration path (hooks keep working standalone until cutover), how tests/hooks/*.test.sh contracts carry over unchanged, and rollback. End with open questions for /writing-plans. This unblocks a future /brainstorming → /writing-plans run; no settings.json change in this task.</action>
  <verify>test -f specs/gate-dispatcher/design.md && grep -q 'first-match-wins' specs/gate-dispatcher/design.md</verify>
  <done>design.md exists, names the rule-table architecture, migration, and rollback; ready for its own PLAN.</done>
</task>
```

### Track 9 — Session/state ledger (idea 9) — kickoff only

#### Task 9.1 — Design doc for the state ledger (no code)

```xml
<task id="9.1" wave="2">
  <files>specs/state-ledger/design.md</files>
  <action>Write the design document (no implementation) for a persistent session/state ledger that grows state-breadcrumb.sh + specs/STATE.md into queryable state, modeled on the claude-code-harness SQLite state machine (report §1.1). MUST cover: schema sketch (sessions, verify_failures, work_states, escalations), the two consumers that exist TODAY — the "same &lt;verify&gt; fails ≥2×" in-flight escalation trigger from rules/orchestration.md (currently relies on orchestrator memory) and cross-session resumption (currently a markdown breadcrumb) — write paths (which hooks append), read paths (which skills query), storage choice consistent with Track 8's ledger decision (this task runs wave 2 so it can read specs/gate-dispatcher/design.md if Track 8 was selected; if not, state the assumption explicitly), and what STATE.md keeps doing (human-readable view stays). End with open questions for /writing-plans.</action>
  <verify>test -f specs/state-ledger/design.md && grep -q 'verify_failures' specs/state-ledger/design.md</verify>
  <done>design.md exists with schema, both named consumers, and alignment to the Track 8 storage decision; ready for its own PLAN.</done>
</task>
```

---

## 6. Risks

| Risk | Track | Mitigation |
|---|---|---|
| `subagent_type: reviewer` not honored by skill-driven dispatch in some runner contexts | 1 | Task 1.2 keeps prompt-level "do not edit" instructions as belt-and-braces; agent def is additive |
| Sha-lint warns on historical plans, creating noise | 3 | Warn-only (exit 0) rollout — mirrors the advisory-first R14 pattern; promote to fail later if signal is clean |
| Renderer flattens checklist `<done>` | 4 | Task 4.2 is test-only with explicit Rule-4 escalation; render_plan.py is never auto-modified |
| Protected-paths hook blocks legitimate harness maintenance | 5 | BREAK_GLASS_REASON escape hatch with audit log; fail-open on parse errors; human approves registration |
| Benchmark fixtures too easy → inflated catch rate | 7 | Defects copied from real bug classes the skills already name; claim-discipline rule limits what the number means |
| Tracks 8/9 design docs drift if only one is selected | 8, 9 | 9.1 explicitly states its storage assumption when 8 is absent |
| Same-wave file overlap if user selects overlapping tracks | 1+2, 3+4 | Wave ordering already encodes it; renumber after selection keeping relative order |

## 7. Status Log

- 2026-06-12 — plan written (status: proposed) — awaiting user track selection; no execution started.
- 2026-06-12 — user selected tracks 1, 2, 6, 7 → execution sub-plan derived at `specs/harness-adoptions-execution/PLAN.md` (task ids preserved). Tracks 3, 4, 5, 8, 9 deferred — this plan stays `proposed` as the umbrella record.
