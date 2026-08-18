# Design — Enforce Simplicity First: prevent over-coding / over-engineering (gh #159)

**Spec source:** https://github.com/minhtran3124/agent-harness/issues/159 (authored by the repo
owner). The issue body plus its own follow-up audit comment (design decisions D1–D5,
implementation plan, acceptance-criteria mapping) together are the approved design. This file
condenses both for local reference — the issue governs on any conflict.

## Problem

`rules/behavior.md` §2 (Simplicity First) states the principle but nothing in the workflow
verifies it. Symptoms: speculative abstractions/config nobody asked for, error handling for
impossible scenarios, 200-line solutions where 50 would do, ceremony creep on tiny reversible
changes, diff lines that don't trace to the request (violates §3 Surgical Changes). This makes
diffs harder to review and lets speculative code become unowned dead weight.

## Where the tree already stands (audited on `loop`, per the issue's own follow-up comment)

| Proposal item | Current state | Remaining work |
|---|---|---|
| 1. Simplicity pass in ship path | `subagent-driven-development` ship chain: spec review → code-quality review → `/correctness-review` → `/intent-review` → receipt. No simplicity pass; `correctness-review/SKILL.md:167` only mentions `/code-review` as a sibling, nothing invokes it. | Insert one step into `sdd/SKILL.md`. |
| 2. Excess detection in `intent-review` | Mostly exists: `intent-reviewer-prompt.md:85-86` already defines `excess` as "Extra features, options, endpoints, abstractions not traceable to any intent clause"; algorithm step 3 scans for it. | ~2-line wording diff: add "config knobs / new public surface" + "flag by default". |
| 3. Diff-size sanity signal | Not present. `hooks/risk-corroboration.sh` already reads `Lane:` + the staged diff. | Add a warn-only line-count check to the existing hook (no new hook). |
| 4. Implementer prompt guardrails | Half-done: `implementer-prompt.md:88` has a trailing self-check ("Did I avoid overbuilding (YAGNI)?") but no dispatch-time constraint up front. | Restate the 3 constraints at the top of the prompt. |

## Goal

Make simplicity a checked gate rather than an aspiration, without adding a new block-mode gate
or a brand-new hook — strengthen existing skills/prompts/hooks per the issue's scope note.

## Non-goals (from the issue, binding)

- No new hook, no new gate mode.
- No block-mode enforcement — diff-size signal and simplify pass stay warn/report-only surfaced
  to the agent, not a commit blocker.
- Not a rewrite of `/simplify`, `intent-review`, or `risk-corroboration.sh` — targeted insertions
  only.

## Design decisions (from the issue's audit comment)

- **D1 — One simplify skill, not three.** Wire the harness-native `/simplify` (classify +
  apply, no plugin dependency) into the ship path. The plugin variants (`ce-simplify-code`,
  `ce-code-simplicity-reviewer`) stay available for manual use only.
- **D2 — Placement & ordering.** Run `/simplify` after the per-task code-quality review and
  before `/correctness-review`, so the correctness/intent oracles review the already-shrunk
  surface. Re-run the task's tests after the simplify apply (sdd already loops tests per task).
- **D3 — Pre-ship deletion vs Rule-4 (ordering conflict).** `intent-review/SKILL.md:121-124`
  makes `excess` report-only because deleting *shipped* functionality is a Rule-4 human
  decision. Carve-out, stated once in each file: the simplify pass edits an **unmerged,
  pre-ship diff** (deletion allowed there); `intent-review`'s `excess` verdict is a **post-hoc**
  check on the final diff (stays report-only).
- **D4 — Threshold trigger instead of lane-manual.** Run `/simplify` when the accumulated diff
  has **≥10 substantive (non-docs/format/lockfile) changed lines**; skip otherwise. This
  auto-exempts tiny 5-line fixes while still catching a tiny-lane 300-line diff — the exact case
  the diff-size signal (item 3) worries about.
- **D5 — Diff-size signal.** Extend `risk-corroboration.sh`: after existing lane corroboration,
  warn (never block) when changed-line count is out of proportion to the declared lane
  (suggested thresholds: >150 lines for `tiny`, >600 for `normal`), printing a note suggesting
  `/simplify`.

## Acceptance criteria (from the issue)

1. A simplification/YAGNI check runs on the ship path for normal and high-risk lanes
   (auto-triggered by the D4 threshold rather than lane-manual — strictly stronger).
2. `intent-review` guidance explicitly calls out unrequested abstractions/config/flexibility as
   `excess` findings by default.
3. Implementer dispatch prompt restates the Simplicity First constraints at the top, not only in
   the trailing self-check.
4. No new block-mode gate — diff-size signal and simplify insertion are warn/apply-in-diff only.
