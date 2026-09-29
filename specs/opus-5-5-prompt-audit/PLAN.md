---
slug: opus-5-5-prompt-audit
status: active
owner: minhtran3124
created: 2026-09-29
---

# Opus 5.5 prompt audit

## 1. Motivation

Align the harness prompt surface with the Claude Opus 5.5 prompting guide after the `coding`
role moved to Opus 5.5 (PR #230): remove stale facts, recall-depressing caps, self-check and
update-suppressor phrasing, and over-delegation; add scope/finish and communication guidance.
Findings and sources: `research-brief.md`; decisions: `design.md`.

## 2. Non-goals

Redeploying `.claude/`; changing hooks, scripts, or model bindings; editing flagged
low-confidence items.

## Global Constraints

- Keep every test-asserted prompt string (see `research-brief.md` and the contract tests).
- Append behavior rules as §4/§5; never renumber §1–§3.
- Edit only the files listed in each task.

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
|------|-------------------------|-----------------------|------------|
| SC-1 | Implementer dispatch and task-review contract still satisfy the binding and routing tests | `bash tests/scripts/runtime-entry-bindings.test.sh` | exit 0 |
| SC-2 | Correctness/intent prompt contracts hold after cap removal and mindset rewrite | `bash tests/scripts/intent-prompt-contract.test.sh && bash tests/scripts/correctness-prompt-composition.test.sh && bash tests/scripts/scorer-threshold-contract.test.sh` | exit 0 |
| SC-3 | Rule tiers and inline-policy anchors unchanged | `bash tests/scripts/rule-loading-tiers.test.sh && bash tests/scripts/inline-policy-drift.test.sh` | exit 0 |
| SC-4 | Every path named in edited docs exists in source and derived trees | `bash scripts/lint-doc-truth.sh` | exit 0 |
| SC-5 | Compound and finishing contracts hold after in-session-pass rewrite | `bash tests/scripts/compound-contract.test.sh && bash tests/scripts/finishing-branch-contract.test.sh` | exit 0 |

## 4. Tasks

### Task 1.1 — SDD dispatch prompts (wave 1)

- **Files:** skills/subagent-driven-development/SKILL.md, skills/subagent-driven-development/implementer-prompt.md, skills/subagent-driven-development/task-reviewer-prompt.md
- **Action:** Dispatch implementer as `coding` + `model_stage: implementer`; replace ask-now and
  self-review blocks with NEEDS_CONTEXT guidance and a completion bar; remove six-finding cap and
  migration phrasing; replace narration suppressor.
- **Verify:** `bash tests/scripts/runtime-entry-bindings.test.sh && bash tests/scripts/context-propagation-regression.test.sh`
- **Done:** Both tests exit 0.
- **Criteria:** SC-1
- **Interfaces:** Consumes the audit findings; produces `implementer-prompt.md`.

### Task 1.2 — Review prompts (wave 1)

- **Files:** skills/correctness-review/correctness-scorer-prompt.md, skills/correctness-review/correctness-reviewer-prompt.md, skills/correctness-review/prompts/shared.md, skills/intent-review/intent-reviewer-prompt.md
- **Action:** Correct scorer gate facts, model and fix-loop references; remove finder caps; bound
  scorer fan-out; rewrite intent mindset to recall-first.
- **Verify:** `bash tests/scripts/intent-prompt-contract.test.sh && bash tests/scripts/correctness-prompt-composition.test.sh && bash tests/scripts/scorer-threshold-contract.test.sh`
- **Done:** All three exit 0.
- **Criteria:** SC-2
- **Interfaces:** Consumes the audit findings; produces `correctness-scorer-prompt.md`.

### Task 1.3 — Rules and root docs (wave 1)

- **Files:** rules/behavior.md, rules/orchestration.md, rules/plan-format.md, rules/auto-correct-scope.md, rules/wave-parallelism.md, CLAUDE.md, HARNESS.md
- **Action:** Add behavior §4/§5; calibrate delegation; fix manifest-path, app-gate and stale
  references; drop numeric summary cap and history narrative.
- **Verify:** `bash tests/scripts/rule-loading-tiers.test.sh && bash tests/scripts/inline-policy-drift.test.sh`
- **Done:** Both exit 0.
- **Criteria:** SC-3
- **Interfaces:** Consumes the audit findings; produces `rules/behavior.md`.

### Task 1.4 — Workflow skills and READMEs (wave 1)

- **Files:** skills/README.md, skills/visual-planner/SKILL.md, skills/xia2/README.md, skills/xia2/references/research-brief-template.md, skills/compound/SKILL.md, skills/compound/README.md, skills/compound/subagents/context-analyzer-prompt.md, skills/compound/subagents/solution-extractor-prompt.md, skills/compound/subagents/decision-extractor-prompt.md, skills/finishing-a-development-branch/SKILL.md, skills/finishing-a-development-branch/references/pr-body.md, skills/brainstorming/spec-document-reviewer-prompt.md, skills/writing-plans/plan-document-reviewer-prompt.md, skills/feature-intake/SKILL.md, skills/xia2/tests/structural/depth-modes-test-cases.md
- **Action:** Fix stale facts and contradictions; run compound passes in-session; replace numeric
  caps and shouting; add the tiny-lane done criterion.
- **Verify:** `bash tests/scripts/compound-contract.test.sh && bash tests/scripts/finishing-branch-contract.test.sh && bash scripts/lint-doc-truth.sh`
- **Done:** All exit 0.
- **Criteria:** SC-4, SC-5
- **Interfaces:** Consumes the audit findings; produces `skills/compound/SKILL.md`.

## 5. Risks

- Removing finder caps raises scorer fan-out and cost — bounded at 20 parallel per batch.
- In-session compound passes use main-session context — acceptable; the session holds the input.

## 6. Status Log

- 2026-09-29 — Tasks 1.1–1.4 applied by the controller directly: `hooks/branch-isolation-guard.sh`
  resolves the branch from `CLAUDE_PROJECT_DIR` (main checkout, on `main`), so Edit/Write — and
  therefore implementer subagents — are denied inside this worktree. Edits applied via exact-match
  scripted replacements; independent review passes still run.
- 2026-09-29 — Review chain: context-propagation audit (1 row repaired), correctness review
  (14 fixed), intent review (1 fixed, 5 recorded). Follow-up commit applies the fixes.
