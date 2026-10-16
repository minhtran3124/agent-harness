# Intent: Grill the design frontier in rounds inside brainstorming

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

`skills/brainstorming/SKILL.md` step 2 asks "one clarifying question per message". A design with
many open decisions then takes many round trips, and the agent may silently assume an answer to
a question it never asked. The agent may also ask the user for facts it could find itself in the
codebase or docs. Pocock's `grilling` skill went through the same design and changed it after
measurement: the same 13 questions landed in about 3 rounds instead of 13.

## Proposed outcome

Step 2 of `skills/brainstorming/SKILL.md` makes the agent do this:

1. Map the open decisions as a design tree.
2. Find the frontier: each decision whose prerequisites the user already settled.
3. Ask the whole frontier in one numbered round.
4. Give a recommended answer for each question, worded so that "yes" accepts it.
5. Dispatch a subagent to find any fact; never ask the user for a fact.
6. Give each decision to the user, then wait.
7. Act only after the user confirms a shared understanding.

The existing rule "if a question goes unanswered or evasive twice, name the gap and move on"
stays, for decisions only.

## Affected users and systems

Users who answer design questions during brainstorming; the agent running `brainstorming` on the
high-risk route and on a real design fork.

## Constraints

- Only step 2 of `skills/brainstorming/SKILL.md` changes. Steps 3–5 (approaches, per-section
  confirmation, restatement) and the HARD-GATE stay as they are.
- Only the high-risk path and the design-fork path run brainstorming; the normal lane's
  notify-and-proceed flow does not change.
- The skill stays under the 600-word ceiling, met by the deletion-test procedure in
  `docs/solutions/harness/deletion-test-for-word-ceiling.md`.
- Edited agent prose follows `skills/asd-ste100/SKILL.md`.
- PR targets `sdlc`.

## Out of scope

- A question cap or a fixed number of rounds.
- Changes to `feature-intake`, `xia2`, `writing-plans`, or any hook.
- A separate `grilling` skill.

## Open questions

- The issue's proof is a recorded live brainstorming session on a real design fork, counted for
  rounds. That needs a real fork and the user's time. Whether a scripted blind run of the skill
  on a fixture design question is enough instead (assumed: research decides; if neither is
  practical, the round count is reported as not auto-verified).

## What success looks like

- `skills/brainstorming/SKILL.md` step 2 states each of the seven behaviors above, and the
  evasive-answer rule applies to decisions only.
- No condition word is lost from the rest of the skill (`scripts/check_scope_qualifiers.py`
  resolution and the task reviewer's meaning verdict).
- On one brainstorming run over a design fork, the frontier closes in three rounds or fewer
  (assumed measure; see Open questions).

## Original request

merge it, re-install with latest code on sdlc branch and start for next gh issue

Issue #309, as referenced (https://github.com/minhtran3124/agent-harness/issues/309):

> **Phase 1: conversation and record prose.** Roadmap: https://claude.ai/artifact/AohXkjEsZKRDXhHheAsrtW
>
> Goal: Ask design questions in rounds, not one per message.
>
> Steps: Rewrite step 2 of `skills/brainstorming/SKILL.md` (442 words) so that the agent does
> this: (1) Map the decisions as a design tree. (2) Find the frontier: each decision for which the
> user already settled the prerequisites. (3) Ask the whole frontier in one numbered round.
> (4) Give a recommended answer for each question. Word the question so that "yes" accepts the
> recommended answer. (5) Dispatch a sub-agent to find any fact. Do not ask the user for a fact.
> (6) Give each decision to the user, then wait. (7) Act only after the user confirms a shared
> understanding. Keep the current rule "move on after two evasive answers" for decisions only.
>
> Scope guard: Only the high-risk path and the design-fork path run brainstorming. The
> notify-and-proceed flow of the normal lane does not change.
>
> Lane: normal, with a context-propagation-audit. Dependencies: None.
>
> Proof: (1) Record one brainstorming session on a real design fork. (2) Count the rounds and the
> questions. (3) The issue passes when the frontier closes in three rounds or fewer.
>
> Source: Pocock, `grilling/SKILL.md`. CHANGELOG: "Same 13 questions land in ~3 rounds instead of 13."
