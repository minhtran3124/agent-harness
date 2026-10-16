# Intent: Deletion-test procedure for the 600-word skill ceiling

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

`scripts/audit_skill_prompts.py` blocks any `skills/*/SKILL.md` over 600 words, but it only
reports a count. Nothing says how to get under the ceiling, so authors trim words. Two recorded
trims lost instructions and no check caught the loss: an STE rewrite of `feature-intake` dropped
two conditions (`docs/solutions/critical-patterns.md`), and a trim in `intent-md-entry` silently
dropped five instructions (`specs/intent-md-entry/SUMMARY.md`). Three skills now sit at or near
the ceiling (`session-retro` 600, `feature-intake` 598, `finishing-a-development-branch` 589),
so every later roadmap item that adds a sentence to them (#310, #312, #313, #318) is blocked
until room is made safely.

## Proposed outcome

1. The ceiling failure message in `scripts/audit_skill_prompts.py` states a procedure, not just
   a count, and points to a harness-owned reference that states it in full: list each sentence,
   ask whether the model already does it by default, delete the whole sentence when yes, never
   shorten a sentence that holds a condition word.
2. That reference is a knowledge entry under `docs/solutions/` (amended 2026-10-16, design D1).
   `skills/asd-ste100/` is a vendored upstream copy whose `UPSTREAM.md` allows no further
   differences, so it is not edited.
3. The two open 2026-10-15 rows in `docs/harness-experimental/improvement-backlog.md` are marked
   done. Their guardrails already shipped before this work (up to commit `23438c1`):
   - the task reviewer's spec verdict runs a meaning-equivalence check on every changed prose
     file without a plan asking for it (`skills/subagent-driven-development/task-reviewer-prompt.md`);
   - `scripts/check_scope_qualifiers.py` lists each condition word a removed prose line had and
     no added line in the same hunk has, shown as an advisory section of the review package
     beside `## STE lint` (`skills/subagent-driven-development/scripts/review_package.py`).
4. The procedure is applied once to `session-retro`, `feature-intake` and
   `finishing-a-development-branch`, bringing each to at least 60 words under 600 with no
   condition lost.

## Affected users and systems

Agents and humans who author or trim skill prose; the task reviewer in
`subagent-driven-development`; the review package builder; three core workflow skills
(`feature-intake` routes every change, `session-retro`, `finishing-a-development-branch`).

## Constraints

- The 600-word ceiling stays. The audit script stays a counter; only its message changes.
- The qualifier check is advisory. It never blocks a commit or a review.
- Edits to the three skills either delete whole sentences or move whole blocks that only some
  branches reach into the skill's `references/`, leaving a one-line pointer (amended 2026-10-16,
  design Architecture §2 and D4). No sentence that holds a condition word (if, unless, only,
  when, never, except, for a new, without) is shortened. A moved or deleted sentence that sat
  under a leading condition keeps that condition in scope for every sentence that still
  depends on it.
- Agent prose that is edited follows `skills/asd-ste100/SKILL.md`.
- PR targets `sdlc`.

## Out of scope

- Changing the ceiling value or exempting more skills.
- Any `hooks/` change.
- Adding the sentences that #310, #312, #313 and #318 need; this work only frees the room.
- Editing `skills/asd-ste100/` or its `UPSTREAM.md` (amended 2026-10-16, design D1).
- A new blind task-review eval or a `rules/terminology.md` entry (amended 2026-10-16, design D2).

## Open questions

- none. The earlier question about a blind task-review eval fixture was closed by design D2: the
  proof uses the shipped qualifier check and the reviewer's meaning verdict.

## What success looks like

- The three skills are each at least 60 words under 600.
- Every condition word that `scripts/check_scope_qualifiers.py` lists for their diffs is resolved
  as kept, citing the line that keeps it, and the task reviewer's meaning verdict is `pass` for
  each changed skill file.
- The two backlog rows show `done`.

## Original request

start for #308

Issue #308, as referenced (https://github.com/minhtran3124/agent-harness/issues/308):

> **Phase 0: make room.** Roadmap: https://claude.ai/artifact/AohXkjEsZKRDXhHheAsrtW
>
> Goal: Meet the 600-word skill ceiling with a deletion test. Delete whole sentences. Do not trim
> words.
>
> Steps: (1) In `scripts/audit_skill_prompts.py`, replace the word-count failure message with this
> procedure: list each sentence; ask: does the model already do this by default?; if yes, delete
> the whole sentence; do not shorten a sentence that contains a condition word. (2) Add the same
> procedure to the STE-flavored mode of `skills/asd-ste100/SKILL.md`. (3) Promote the two open
> rows dated 2026-10-15 in `docs/harness-experimental/improvement-backlog.md`: a
> meaning-equivalence instruction in the spec verdict of `task-reviewer-prompt.md`, and
> `scripts/check_scope_qualifiers.py` as an advisory section of the review package beside
> `## STE lint`. (4) Apply the procedure to `session-retro` (600 words), `finishing-a-development-branch`
> (589), `feature-intake` (598). Free at least 60 words in each.
>
> Lane: normal, with a context-propagation-audit. Dependencies: none; blocks #310, #312, #313.
> Proof: run `scripts/run_task_review_eval.py` and `scripts/score_task_review_eval.py` on the three
> edited skills with the condition-word list as the observable; pass = zero lost conditions;
> record beside the A/B in `rules/terminology.md`.

Change request, 2026-10-16, verbatim reply to escalation E001 in `ESCALATIONS.md`:

A

Option A as offered in E001: "Amend `intent.md` to match the approved design (D1, D2, the
block-move rule, and "at least 60 words under 600" as the measure), commit it, and re-pin the
slug through feature-intake's re-pin procedure. Then re-run intent review against the new pin.
No code change."
