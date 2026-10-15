# ste100-prose-rollout — Design

Written 2026-10-15. Pins: repo 48e7e05

## Goal

Roll the ASD-STE100 rewrite out to the remaining agent-executed prose (Phase 3 of
`specs/ste100-harness-prose/design.md`). First add four guardrails, so that a rewrite cannot drop
a scope qualifier without a reviewer
seeing it, and cannot raise any file's lint count.

## Current state

- PR #293 (`docs/ste100-harness-prose`, open) shipped Phases 1–2: the vendored skill
  `skills/asd-ste100/`, the `## STE lint` section in
  `skills/subagent-driven-development/scripts/review_package.py`, the warn-only ratchet
  `scripts/check_ste_baseline.py` with `scripts/ste-baseline.json`, and three pilot rewrites.
- The pilot passed (`specs/ste100-harness-prose/DECISION.md`, 80 trials). Parent design D2 and D6
  allow Phase 3.
- The pilot rewrite dropped two scope qualifiers. Only a meaning-equivalence review that the task
  brief asked for caught them (`docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`).
  `skills/subagent-driven-development/task-reviewer-prompt.md` has no such instruction.
- 43 in-scope files hold 267 hard findings (measured 2026-10-15 `scripts/ste-baseline.json`).
- `skills/feature-intake/SKILL.md` is at 599 of 600 words (measured 2026-10-15 `wc -w`). Its
  "Research-depth handoff" section repeats the lane-to-depth mapping that the always-on
  `rules/research-depth.md` already states.

## Approaches considered

Room for the tiny-lane line in `feature-intake`:

- **Chosen:** replace the duplicate "Research-depth handoff" section with a one-line pointer to
  `rules/research-depth.md`. No rule is lost, because the rule file is always loaded.
- Put the line in `rules/auto-correct-scope.md`. Rejected: that file loads only on a `specs/**`
  read, so a tiny-lane agent may never see it.
- Move the Step 6 SUMMARY block into `references/`. Rejected: it adds a read on every intake.

Wave execution:

- **Chosen:** sequential waves, one implementer and one task review each.
- Parallel implementers inside a wave. Rejected: the shared git index is a known hazard
  (`docs/solutions/harness/parallel-implementers-share-one-git-index.md`), and parallel reviews
  give no gain on a prose task.

## Architecture

### Phase A — guardrails (before any rewrite)

- **A1 — `scripts/check_scope_qualifiers.py`.** Input: BASE and HEAD. It reads the unified diff of
  `.md` files under `skills/`, `rules/`, `agents/` (the same roots as `## STE lint`). For each
  hunk, it lists each condition word (`if`, `unless`, `only`, `when`, `never`, `except`,
  `for a new`, `without`) that a removed line has and no added line in the same hunk has. Words
  match whole words and ignore case (`When` matches `when`; `commonly` does not match `only`). Output
  lines: `<file>:<hunk old start>: dropped "<word>": <removed line, trimmed>`. On any error it
  prints `scope-qualifiers: unavailable (<reason>)` and exits 0. `review_package.py` adds the
  output as `## Scope qualifiers` after `## STE lint`. The section is advisory.
- **A2 — reviewer meaning check.** `task-reviewer-prompt.md` gets a spec-verdict instruction: for
  each changed prose file, compare each removed line with its replacement. A dropped condition,
  exception, hedge or scope qualifier is an Important spec finding. Each `## Scope qualifiers`
  line is resolved as either "kept elsewhere" (cite the line) or a finding.
- **A3 — tiny-lane line.** In `skills/feature-intake/SKILL.md`, replace "Research-depth handoff"
  with a one-line pointer to `rules/research-depth.md`. Extend the tiny route: apply
  `skills/asd-ste100/SKILL.md` to agent prose that you edit. The file stays at 600 words or fewer
  (budget). A3's checks include `check_ste_baseline.py --strict --against 48e7e05`, because no
  rewrite wave touches `skills/feature-intake/SKILL.md` after A3. A4 therefore lands before A3.
- **A4 — per-file ratchet against the start.** `scripts/check_ste_baseline.py` gets
  `--against <git-ref>`: it compares each file's current hard count with that file's entry in
  `scripts/ste-baseline.json` at `<git-ref>` (read with `git show`), and prints a WARN line for
  each rise. `--strict` exits 1 on a WARN line and also on a `ste-baseline: skipped` line, so a
  skipped run is never read as a pass. Without `--strict`, behavior stays warn-only. This
  reverses a tested behavior on purpose: the four `*_skips_and_exits_0` tests in
  `scripts/test_check_ste_baseline.py` and the script's docstring change to expect exit 1 under
  `--strict`. `test_non_int_baseline_value_skips_and_exits_0` loops over both modes, so it is
  split: the default run still asserts exit 0. The change tightens the check, so it is not `weakening-validation`. `--against`
  names a commit; the plan pins the start of this PR (`48e7e05`), and a rebase onto a changed
  `docs/ste100-harness-prose` re-pins it to the new merge-base. A4 touches `scripts/`, so
  `scripts/ci-strict-gate.sh` reports it in its warn tier; this is expected.

### Phase B — rollout (nine sequential waves)

| Wave | Files |
|---|---|
| B1 | `rules/plan-format.md`, `rules/auto-correct-scope.md`, `rules/terminology.md` |
| B2 | `rules/behavior.md`, `rules/research-depth.md`, `rules/review-policy.md`, `rules/wave-parallelism.md`, `rules/architecture.md` |
| B3 | `agents/PROJECT.md`, `agents/README.md`, `agents/coding.md`, `agents/reviewer.md`, `agents/task-reviewer.md`, `agents/test-runner.md` |
| B4 | `skills/brainstorming/SKILL.md`, `skills/writing-plans/SKILL.md`, `skills/writing-plans/references/review-loop.md`, `skills/feature-intake/references/draft-intent.md`, `skills/feature-intake/references/re-pin.md` |
| B5 | `skills/xia2/SKILL.md`, `skills/xia2/README.md`, `skills/xia2/references/depth-classifier.md` |
| B6 | `skills/correctness-review/SKILL.md`, `skills/correctness-review/correctness-reviewer-prompt.md`, `skills/correctness-review/correctness-scorer-prompt.md`, `skills/intent-review/SKILL.md`, `skills/intent-review/intent-reviewer-prompt.md`, `skills/context-propagation-audit/SKILL.md` |
| B7 | `skills/subagent-driven-development/implementer-prompt.md`, `skills/subagent-driven-development/task-reviewer-prompt.md`, `skills/subagent-driven-development/references/resume.md`, `skills/subagent-driven-development/references/review-chain.md`, `skills/using-git-worktrees/SKILL.md` |
| B8 | `skills/finishing-a-development-branch/SKILL.md`, `skills/finishing-a-development-branch/references/pr-body.md`, `skills/session-retro/SKILL.md`, `skills/visual-planner/SKILL.md`, `skills/visual-planner/references/review-sidecar.md` |
| B9 | `skills/compound/SKILL.md`, `skills/compound/README.md`, `skills/compound/subagents/context-analyzer-prompt.md`, `skills/compound/subagents/decision-extractor-prompt.md`, `skills/compound/subagents/related-docs-finder-prompt.md` |

Each wave: the implementer reads `skills/asd-ste100/SKILL.md` and the scope-qualifier failure
record, and rewrites the files in STE-flavored mode (as in the pilot). It then runs
`python3 scripts/check_ste_baseline.py --strict` **before** `--update`, so a rise in any file
fails the wave before the baseline absorbs it. Then it runs `--update` and
`bash scripts/run-tests.sh`. The task
reviewer gets a review package with `## STE lint` and `## Scope qualifiers`, and gives a meaning
verdict per file. A file at the 600-word ceiling keeps its hard sentences long. SUMMARY lists
them as "kept long on purpose". B7 rewrites the task-reviewer prompt after A2 changed it, so
B7's checks include the A2 propagation test: the rewrite cannot weaken the meaning instruction
unseen.

## Error behavior

- A meaning loss gets one fix round (budget). A second fail leaves that file at its base text and logs it
  under `### Deviations`.
- A rewrite that breaks a literal-grep test: fix the prose, never the test (`weakening-validation`).
- `check_scope_qualifiers.py` fails: the section reads `scope-qualifiers: unavailable (<reason>)`.
  The review does not block on that line alone. The meaning check in A2 still runs.
- `ste-lint` unavailable: the reviewer does not approve the quality verdict (unchanged from
  Phase 1).

## Tests

- A1: unit tests for a dropped `if` (listed), a condition moved to another added line in the same
  hunk (not listed), whole-word and case rules (`When` listed, `commonly` not), a non-prose path
  (ignored), and a git failure (`unavailable`, exit 0). Replays of the pilot's two drops: the
  Step 6 cut is listed; the Step 1 split is not listed (known limit, see A3). A review-package test for the new section. Truth tier.
- A2: a context-propagation assertion that the prompt holds the instruction, and a mutation case
  that removes it. Traceability tier.
- A3: `scripts/audit_skill_prompts.py` word ceiling, and an assertion that
  `rules/research-depth.md` still holds each rule the removed section carried: `high-risk` → Deep,
  `normal` → Standard, `tiny` → Quick only when every Quick condition passes, and depth moves up
  on evidence but never down. Traceability tier.
- A4: tests for `--against` (a rise against the ref is a WARN; `--strict` exits 1) and for
  `--strict` on a skipped run (exit 1). Truth tier.
- Each wave: `python3 scripts/check_ste_baseline.py --strict` exits 0 before `--update`, and
  `bash scripts/run-tests.sh` is green. The meaning verdict is a review, not a test.

## Success criteria

- `check_scope_qualifiers.py` tests pass, and `review_package.py` prints `## Scope qualifiers`.
- The A4 tests pass: `--against` warns on a rise, and `--strict` exits 1 on a WARN or a skip.
- The task-reviewer prompt holds the meaning instruction, and its propagation test passes.
- `feature-intake/SKILL.md` has the tiny-lane line and is at 600 words or fewer.
- After B9, `python3 scripts/check_ste_baseline.py --strict --against 48e7e05` exits 0: no file's
  hard count is above its value at the start of this PR (per file, as intent.md requires).
- After B9, the sum of hard counts for the 43 files is lower than 267 (measured 2026-10-15
  `scripts/ste-baseline.json`).
- Each of the 43 files has a task-review meaning verdict in the SDD ledger. A file left at its
  base text after a second fail still counts: its verdict is recorded as a fail, with its
  `### Deviations` entry.

## Non-goals

- Eval fixtures, templates, the vendored skill, the three pilot files, and files with a baseline
  count of 0.
- A new paid comprehension pilot.
- The consumer `PROSE_ROOTS` scope and the other advisory findings from PR #293.
- Making the qualifier section or the baseline blocking.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | The pilot result transfers to the other files: an STE rewrite with a meaning review does not lower agent comprehension. | none yet: Inference, 2026-10-15, `specs/ste100-harness-prose/DECISION.md` (3 files, at ceiling) | accepted risk: user chose no new pilot (intent.md Out of scope) | A file reads worse to agents. Fallback: `git revert` that wave's commit. |
| A2 | `rules/research-depth.md` holds the full lane-to-depth mapping that the feature-intake section repeats. | provenance: Local, 2026-10-15, `rules/research-depth.md` lines 3–6 | Task A3 assertion | xia2 loses the mapping. Fallback: keep the section and cut words elsewhere. |
| A3 | A per-hunk word diff finds the drop pattern in the failure record (a condition word in a removed line, absent from the hunk's added lines). | truth: Local, 2026-10-15, `git diff -U0 87d204c dc867ed` and `git diff -U0 bb923dc f49a9d1 -- skills/feature-intake/SKILL.md`: partly false. The Step 6 cut drops `for a new` and would be listed; the Step 1 split keeps every condition word in an added line and would not | Task A1 tests that replay both drops | The script misses drops. The A2 reviewer check still runs, so the script is advisory only. |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| The rewrites make agents more accurate. | The pilot measured "no worse" at a ceiling, not "better". |
| `## Scope qualifiers` finds every meaning loss. | It matches eight words per hunk. A drop with no condition word, or a word moved across hunks, is not seen. The reviewer check is the gate. |
| Consumers get the `## Scope qualifiers` section. | `scripts/` does not deploy to consumers, and the user chose to keep it harness-only (2026-10-15). A consumer's package prints `scope-qualifiers: unavailable`; the A2 reviewer check still runs. |
| Consumers see lint on harness prose. | Consumer `PROSE_ROOTS` scope is out of scope. |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | Stack on PR #293: branch from `docs/ste100-harness-prose`. | The PR targets that branch, then is retargeted to `sdlc` after #293 merges. | settled |
| D2 | Scope is 43 agent-prose files. No fixtures, templates, vendored skill, pilot files, or zero-count files. | 267 findings in scope (measured 2026-10-15 `scripts/ste-baseline.json`). | settled |
| D3 | Guardrails A1–A4 land before any rewrite wave. | Every wave gets the reviewer meaning check and the qualifier section. | settled |
| D4 | Room for the tiny-lane line comes from replacing the duplicate research-depth section with a pointer. | The mapping lives only in `rules/research-depth.md`. | settled |
| D5 | Waves run sequentially, one implementer and one task review each, 3–6 files (budget). | Nine waves. No shared-index risk. B1 has 3 files because they are the three largest rules (57 findings, measured 2026-10-15 `scripts/ste-baseline.json`; 3,322 words, measured 2026-10-15 `wc -w`); B5 has 3 because the xia2 family has 3 in-scope files. | settled |
| D6 | No new paid pilot. The per-file meaning verdict is the gate. | Assumption A1 is an accepted risk. | settled |
| D7 | `check_ste_baseline.py` gets `--against <git-ref>`, and `--strict` fails on a skipped run. | The per-file success criterion is a re-runnable check. This closes the PR #293 advisory finding "`--strict` exits 0 on a skip". | settled |
