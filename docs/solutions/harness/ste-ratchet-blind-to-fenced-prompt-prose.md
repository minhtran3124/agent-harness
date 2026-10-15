---
problem_type: failure
module: skills/asd-ste100/scripts/ste-lint.py + scripts/check_ste_baseline.py + skills/subagent-driven-development/scripts/review_package.py
tags: [ste100, ste-lint, ratchet-blind-spot, fenced-dispatch-prompt, eval-fixture-scope, advisory-section, green-is-not-correct]
severity: standard
applicable_when: You rewrite agent prose for STE style and use the STE lint count (the baseline ratchet or the review package's `## STE lint` section) as evidence that the rewrite is done, or you plan a rewrite that touches `*-prompt.md` dispatch prompts or eval fixtures.
affects:
  - specs/ste100-prose-rollout/PLAN.md
  - skills/subagent-driven-development/task-reviewer-prompt.md
supersedes: null
confidence: high
confirmed_at: 2026-10-15
---
## Applicable When

You rewrite agent prose for STE style and use the STE lint count as evidence. That count comes
from the baseline ratchet (`scripts/check_ste_baseline.py`) or the review package's `## STE lint`
section. This also applies when you plan a rewrite that touches `*-prompt.md` dispatch prompts or
eval fixtures.

## Symptom

In the ste100-prose-rollout (Phase 3, 43 files), three checks gave a result that did not match
the prose. Each one surfaced mid-run.

- The dispatch prompts (`implementer-prompt.md`, `task-reviewer-prompt.md`,
  `intent-reviewer-prompt.md`, `correctness-scorer-prompt.md`) keep 61 to 100 non-blank lines of
  prompt prose inside a fenced `Task tool (...)` block (measured 2026-10-15 at the rollout HEAD).
  `ste-lint.py` skips fenced blocks. `implementer-prompt.md` showed "hard 1 → 0" when about 30
  fenced lines had changed. That count came from one long sentence outside the fence.
  `task-reviewer-prompt.md` likewise went 1 → 0 from a single semicolon outside its fence.
- The plan's Global Constraints said "never edit fenced code". Read as written, that rule forbade
  the main text of every dispatch prompt in scope.
- The review package lints every `.md` under `skills/`, eval fixtures included. The baseline
  globs stop at `skills/*/*/*.md`, and the intent excluded fixtures. A required test-record edit
  to `skills/xia2/tests/structural/depth-modes-test-cases.md` showed "8 → 35". The reviewer rule
  calls that an Important finding.
- The task-reviewer instruction said "kept" must cite "the HEAD line that keeps the qualifier
  word". Under that wording, an advisory `## Scope qualifiers` line could force a blocking finding
  when the rewrite kept a condition in other words.

## Wrong Approach

The plan treated the lint count as the measure of "STE done". It assumed that the scope of the
lint section, the scope of the ratchet, and the scope of the rewrite are the same set of lines.

## Why It Failed

- A fence means "code" to the linter. In a `*-prompt.md` file the fence holds the prompt itself,
  so the most load-bearing prose in the rollout was the prose that the count could not see.
- Two tools define "prose file" with different globs, so they disagree on fixtures and on
  nesting below three levels.
- The rule that limits a reviewer to the same word turns a list of word-level candidates into a
  verdict on meaning, and that list is advisory by design.

## Correct Approach

- In the plan, state that the fenced dispatch block of a `*-prompt.md` file is prose. Rewrite it
  in Strict mode, and keep every command, path, placeholder and YAML key. This is the Phase 3
  Global Constraints exception, added after Task 1.3.
- Record in `### Not auto-verified` that the lint count does not cover fenced prompt prose. The
  task reviewer's Strict-mode judgement and meaning check are then the only check, so brief the
  reviewer to go through every fenced hunk.
- When an excluded file (an eval fixture) must change, tell the reviewer that it is out of STE
  scope. Record its lint rise as a plan-mandated Minor finding, not an Important one.
- Let "kept" cite the HEAD text that keeps the condition in other words (fixed in `5f408ff`).
- Before you rewrite a skill, search its files for repo-local maintenance rules ("must re-run",
  "When you change"). The `skills/xia2/README.md` structural-suite rule fired on a pure prose
  rewrite. A fresh agent, blind to the diff, ran Run 5, with 30/30 stable.

## Guardrail

proposed: lint the `prompt: |` body of each `*-prompt.md` dispatch block as prose, through a
`--include-fences` mode or a prompt-body extractor in `scripts/check_ste_baseline.py` and
`review_package.py`. The ratchet then measures the dispatch prompts.

proposed: share one prose-path definition between `scripts/check_ste_baseline.py` (GLOBS) and
`review_package.py` (PROSE_ROOTS), and exclude `skills/*/tests/**`. Then the review section and
the ratchet agree on which files count.

## Related

- docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md
- docs/solutions/harness/ratchet-matches-spelling-not-property.md
- docs/solutions/harness/ste100-adoption-decisions.md
