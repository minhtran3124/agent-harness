---
slug: harness-adoptions-execution
status: shipped
owner: Minh Tran
created: 2026-06-12
---

# Harness Adoptions — Execution Plan (Tracks 1, 2, 6, 7)

> **For Claude:** REQUIRED SUB-SKILL: Use subagent-driven-development to implement this plan
> task-by-task (or executing-plans in a parallel session). Final passes: /correctness-review
> then /intent-review against the Intent in specs/harness-adoptions-execution/SUMMARY.md.

**Goal:** Implement the four tracks the user selected from
`specs/harness-comparison-adoptions/PLAN.md` (the decision plan derived from
`docs/research-claude-code-harness-comparison.md`): structurally read-only review agents,
the `not_observed != absent` rule, the integration evidence-tier table, and the
review-chain micro-benchmark with a baseline catch rate.

**Architecture:** Three waves. Wave 1 is four independent tasks (agent definition, behavior
rule, README table, benchmark scaffold). Wave 2 wires the reviewer agent into the three
dispatch prompts and authors the benchmark fixtures. Wave 3 adds the epistemic rule to the
same prompt files (serialized after wave 2 — same files) and runs the benchmark baseline.
Task ids keep their master-plan numbering (1.x, 2.x, 6.x, 7.x) for traceability.

**Tech Stack:** Markdown agent/skill/rule docs; benchmark fixtures as FastAPI-style diffs
per `.claude/rules/architecture.md`; verification via grep/diff/`scripts/lint-doc-truth.sh`.

---

## 1. Motivation

Selected for highest leverage-per-effort: Tracks 1+2 make review independence structural and
name the epistemic rule the reviewers must follow; Track 6 makes integration claims honest;
Track 7 produces the repo's first empirical number for what the review chain actually
catches — and the regression baseline for every future edit to those skills.

## 2. Non-goals

- Tracks 3, 4, 5, 8, 9 of the master plan — deferred, not cancelled (see
  `specs/harness-comparison-adoptions/PLAN.md` §5 for their full task definitions).
- No automated benchmark runner — Track 7 v1 is a manual protocol by design.
- No model pinning in the reviewer agent — callers keep per-pass model choice.

## 3. Success Criteria

- All eight `<verify>` commands exit 0; `bash scripts/run-tests.sh` stays green.
- Dispatching either review skill names an agent type whose tool whitelist excludes
  Write/Edit/Agent (Track 1).
- Both behavior.md copies and both reviewer prompts carry the named `not_observed != absent`
  rule (Track 2).
- `skills/README.md` has the evidence-tier table with the graduation rule, doc-truth lint
  green (Track 6).
- `benchmarks/review-chain/results/2026-06-baseline.md` reports a measured catch rate over
  5 fixtures (Track 7).

---

## 4. Tasks

### Wave 1 — independent foundations

#### Task 1.1 — Create the read-only `reviewer` agent definition

```xml
<task id="1.1" wave="1">
  <files>agents/reviewer.md</files>
  <action>Create agents/reviewer.md following the frontmatter shape of agents/test-runner.md (name, description, tools, model, memory). Set `name: reviewer`; `tools: Glob, Grep, Read, Bash` — deliberately NO Write, NO Edit, NO Agent (structural review independence: the reviewer cannot modify files or spawn nested agents; Bash stays for `git diff`/`git log`/running tests read-only). Omit `model:` (callers pass their own per the ensemble-diversity rule in the reviewer prompts). Body: a short role statement — "You produce findings; you never fix. Your final message is the deliverable." plus a note that any urge to edit a file is itself a finding to report. Acknowledged limitation: Bash remains mutation-capable — the body's "never fix" instruction is the only guard on that channel; the structural guarantee covers Write/Edit/Agent. Keep it under ~40 lines; mirror the tone of agents/test-runner.md.</action>
  <verify>grep -q '^name: reviewer$' agents/reviewer.md && grep -q '^tools: Glob, Grep, Read, Bash$' agents/reviewer.md && ! grep -qE '^tools:.*(Write|Edit)' agents/reviewer.md</verify>
  <done>agents/reviewer.md exists with a tools whitelist excluding Write/Edit/Agent and no model pin.</done>
</task>
```

#### Task 2.1 — Add `not_observed != absent` to behavior guidelines (both copies)

```xml
<task id="2.1" wave="1">
  <files>rules/behavior.md, .claude/rules/behavior.md</files>
  <action>Add one bullet to section "## 1. Think Before Coding" in rules/behavior.md: "- `not_observed != absent` — a missing search result, an unread file, or unavailable memory means *unknown*, not *absent*. Before claiming something does not exist, state where you looked." Apply the identical edit to .claude/rules/behavior.md (the two copies must stay byte-identical — CLAUDE.md names rules/behavior.md as the single source of truth and the doc-truth lint may compare them).</action>
  <verify>grep -q 'not_observed != absent' rules/behavior.md && diff -q rules/behavior.md .claude/rules/behavior.md</verify>
  <done>The named epistemic rule appears in §1 of both behavior.md copies and the copies are identical.</done>
</task>
```

#### Task 6.1 — Integration evidence-tier table in skills/README.md

```xml
<task id="6.1" wave="1">
  <files>skills/README.md</files>
  <action>Add a section "## Integration Evidence Tiers" after "## External Skills": a table with columns Integration | Kind | Tier | Evidence. Rows: each external skill referenced by workflows (systematic-debugging, test-driven-development, requesting-code-review, session-tracker, skill-creator), each MCP dependency (code-review-graph, context7), and the cross-skill handoff edges from the Handoff Map that have actually been exercised (at minimum: subagent-driven-development → correctness-review → intent-review, exercised in the intent-review dogfood — cite commit a2a4349). Tiers: ci-proven (a CI job runs it) / manually-verified (date) (a recorded run exists) / documented-only (never observed here). Close with the graduation rule, quoting the research report: an edge only moves UP a tier when a recorded run exists in this repo — support claims are never inherited (`not_observed != absent`). Be honest: most external-skill rows start at documented-only.</action>
  <verify>grep -q 'Integration Evidence Tiers' skills/README.md && grep -q 'documented-only' skills/README.md && bash scripts/lint-doc-truth.sh</verify>
  <done>skills/README.md carries an honest tier table with the graduation rule; doc-truth lint green.</done>
</task>
```

#### Task 7.1 — Scaffold the benchmark directory + protocol

```xml
<task id="7.1" wave="1">
  <files>benchmarks/review-chain/README.md, benchmarks/review-chain/results/template.md</files>
  <action>Create benchmarks/review-chain/README.md defining the manual v1 protocol: (1) each fixture under fixtures/&lt;name&gt;/ contains intent.md (a verbatim-style user request), diff.patch (a small self-contained diff implementing it with ONE planted defect), and truth.md (the ground-truth finding: defect class, location, and whether /correctness-review or /intent-review should catch it); (2) a run = applying the fixture in a scratch worktree, executing /correctness-review then /intent-review standalone, and scoring each against truth.md as caught / missed / false-positive, recording token cost per pass; (3) results land in results/&lt;date&gt;-&lt;label&gt;.md using results/template.md (columns: fixture, defect class, expected oracle, caught-by, verdict, tokens). State the claim-discipline rule up front, borrowed from the breezing-bench design: the benchmark measures ONLY whether the two review skills catch the planted defect classes — it is not evidence about the full chain. Note: automated runner is explicitly out of scope for v1.</action>
  <verify>test -f benchmarks/review-chain/README.md && test -f benchmarks/review-chain/results/template.md && grep -q 'caught / missed / false-positive' benchmarks/review-chain/README.md</verify>
  <done>Protocol + results template exist; scope and claim limits are stated in the README.</done>
</task>
```

### Wave 2 — wiring + fixtures

#### Task 1.2 — Dispatch the three review passes with `subagent_type: reviewer`

```xml
<task id="1.2" wave="2">
  <files>skills/correctness-review/correctness-reviewer-prompt.md, skills/correctness-review/correctness-scorer-prompt.md, skills/intent-review/intent-reviewer-prompt.md</files>
  <action>In each of the three prompt files, find the single fenced `Task tool` dispatch block (headed `Task tool (general-purpose):`; it contains a `model:` line — `<different from implementer; ...>` in the two reviewer prompts ~line 25, `<cheap/fast model ...>` in the scorer prompt ~line 23). In each block: update the header to name the reviewer agent type (e.g. `Task tool (reviewer):`) and add `subagent_type: reviewer`, with one explanatory sentence: "reviewer is a read-only agent (no Write/Edit/Agent) — review independence is enforced structurally, not by instruction." Do not change the model lines, other dispatch parameters, or the finding rubrics.</action>
  <verify>grep -q 'subagent_type: reviewer' skills/correctness-review/correctness-reviewer-prompt.md && grep -q 'subagent_type: reviewer' skills/correctness-review/correctness-scorer-prompt.md && grep -q 'subagent_type: reviewer' skills/intent-review/intent-reviewer-prompt.md</verify>
  <done>All three review-pass dispatches name the read-only reviewer agent type.</done>
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

### Wave 3 — same-file follow-ups + baseline

#### Task 2.2 — Enforce `not_observed != absent` inside the two review prompts

```xml
<task id="2.2" wave="3">
  <files>skills/correctness-review/correctness-reviewer-prompt.md, skills/intent-review/intent-reviewer-prompt.md</files>
  <action>In each reviewer prompt's finding-requirements section, add a requirement named `not_observed != absent`: any finding (or all-clear claim) that asserts absence — "no callers", "no test covers this", "nothing handles X", "no gap found" — MUST name the locations searched (paths/globs/commands). A claim that cannot cite its search surface is reported as `unknown`, never as absent. Wave 3 because task 1.2 (wave 2) edits the same files.</action>
  <verify>grep -q 'not_observed != absent' skills/correctness-review/correctness-reviewer-prompt.md && grep -q 'not_observed != absent' skills/intent-review/intent-reviewer-prompt.md</verify>
  <done>Both reviewer prompts require absence-claims to cite their search surface or downgrade to unknown.</done>
</task>
```

#### Task 7.3 — Baseline run + first catch-rate number

```xml
<task id="7.3" wave="3">
  <files>benchmarks/review-chain/results/2026-06-baseline.md</files>
  <action>Execute the 7.1 protocol once over all 5 fixtures (scratch worktree per fixture; /correctness-review then /intent-review; score vs truth.md). Run this AFTER tasks 1.2 and 2.2 are committed so the baseline measures the upgraded review skills (read-only reviewer agent + epistemic rule) — note the measured skill versions (commit sha) in the results header. Record per-fixture rows plus the headline numbers: catch rate (n/5), false positives, and approximate token cost per pass (from session usage). Honesty rules from the protocol apply: report misses plainly; do not re-run a fixture until it passes; if a skill catches the defect for the wrong reason, score it caught-wrong-reason and say so. This file is the repo's first empirical claim about the review chain — and the regression baseline for any future edit to the two review skills.</action>
  <verify>test -f benchmarks/review-chain/results/2026-06-baseline.md && grep -qi 'catch rate' benchmarks/review-chain/results/2026-06-baseline.md</verify>
  <done>Baseline results file exists with per-fixture verdicts, the measured skill commit sha, and a headline catch rate.</done>
</task>
```

---

## 5. Risks

| Risk | Task | Mitigation |
|---|---|---|
| `subagent_type: reviewer` not honored in some runner contexts | 1.2 | Prompt-level "do not edit" instructions stay as belt-and-braces; agent def is additive |
| Reviewer's Bash channel can still mutate | 1.1 | Known limitation, stated in the agent body; structural guarantee covers Write/Edit/Agent |
| Benchmark fixtures too easy → inflated catch rate | 7.2 | Defects copied from real bug classes the skills already name; claim-discipline rule limits what the number means |
| 2.2 lands while 1.2 in flight → merge conflict | 2.2 | Wave 3 serialization after wave 2; zero same-wave file overlap throughout |
| Baseline measures pre-upgrade skills | 7.3 | 7.3 explicitly runs after 1.2 + 2.2 commits and records the sha it measured |

## 6. Status Log

- 2026-06-12 — sub-plan derived from specs/harness-comparison-adoptions/PLAN.md (tracks 1, 2, 6, 7 selected by user; tasks reviewer-approved there; ids kept for traceability). Status: active.
- 2026-06-12 — execution mode chosen: parallel session via /executing-plans (checkpoint-based).
- 2026-06-12 — executed in-place on branch feat/enhance-skills. All 8 tasks done, all `<verify>` exit 0, `scripts/run-tests.sh` green (85 passed, 1 skipped). Per-wave commits:
  - Wave 1 — `9a0c95e` (1.1 reviewer agent, 2.1 epistemic rule, 6.1 evidence tiers, 7.1 benchmark scaffold)
  - Wave 2 — `5b5d5b6` (1.2 reviewer wired into 3 dispatches, 7.2 five fixtures)
  - Wave 3 — `4d3a401` (2.2 rule enforced in 2 reviewer prompts), `6333b70` (7.3 baseline — catch rate 5/5, 0 hard false positives)
  - Open follow-ups (from 7.3 baseline caveats): register the `reviewer` agent type then re-measure with `subagent_type: reviewer`; make the two intent fixtures runtime-clean.
- 2026-06-12 — shipped via `feat/enhance-skills` (PR #17, whole-branch PR against main).
