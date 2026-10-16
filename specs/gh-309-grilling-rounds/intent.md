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

1. Map the open decisions as a design tree. The tree holds purpose, constraints, success
   criteria and boundaries. Approach choice belongs to step 3; section detail belongs to step 4.
2. Find the frontier: each decision whose prerequisites the user already settled.
3. Ask the whole frontier in one numbered round.
4. Give a recommended answer for each question, worded so that "yes" accepts it. No fixed
   template or emoji is required.
5. Find each fact itself, or dispatch a subagent when the search is larger than a few reads;
   never ask the user for a fact.
6. Give each decision to the user, then wait.
7. Step 2 ends when the frontier is empty and the user confirms a shared understanding. A
   plain "yes" to the whole last round is that confirmation; otherwise the agent asks for it.
   Act only after it.

The existing rule "if a question goes unanswered or evasive twice, name the gap and move on"
stays, for decisions only: name the gap, record the recommended answer as an assumption, and
move on. The sentence "Do not over-probe: steps 3–4 still catch any gap ..." is replaced by the
tier boundary in behavior 1 and the stop condition in behavior 7.

## Affected users and systems

Users who answer design questions during brainstorming; the agent running `brainstorming` on the
high-risk route and on a real design fork.

## Constraints

- Only step 2 of `skills/brainstorming/SKILL.md` changes. Steps 3–5 (approaches, per-section
  confirmation, restatement), the HARD-GATE, the visual-artifact sentence, and
  `references/design-template.md` stay as they are. A paraphrase of the old step-2 rhythm in
  another file, found by the context-propagation audit, is updated to match.
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
- A design-tree field in `design.md`; the tree lives in the conversation only.
- A repo test (under `tests/` or wired into CI) that greps the step-2 wording. A spec-local
  check script under `specs/gh-309-grilling-rounds/` is allowed.
- Keeping step-2 questions at the requirements tier. Issue #321 owns that, with its own blind
  run (`ESCALATIONS.md` E002).

## Proof

- Before merge: one blind run of the new step-2 text by a subagent on a fixture design
  question with an answer key of about 10–13 rows, with a second subagent answering as the
  user. The number of rows the fixture text leaves open is recorded beside it. The transcript
  is recorded under `specs/gh-309-grilling-rounds/`, with the round count and the question
  count, marked "(assumed)". A step-2 question that asks the user for a fact is a failure. The
  count of approach-level or implementation-level questions is recorded as advisory
  (`ESCALATIONS.md` E002).
- Rounds are the rounds of new questions until the agent first declares the frontier empty;
  the total turn count is recorded beside it (`ESCALATIONS.md` E001).
- After merge: the first real brainstorming session on a design fork is the live evidence. Until
  it exists, the live count is listed under `### Not auto-verified`.
- Static checks: `scripts/audit_skill_prompts.py` (ceiling 600 words), the STE lint,
  `scripts/check_scope_qualifiers.py` with every removed condition word cited, and the
  context-propagation audit.

## Open questions

- none

## What success looks like

- `skills/brainstorming/SKILL.md` step 2 states each of the seven behaviors above, and the
  evasive-answer rule applies to decisions only.
- No condition word is lost from the rest of the skill (`scripts/check_scope_qualifiers.py`
  resolution and the task reviewer's meaning verdict).
- On the blind run, the frontier closes in three rounds or fewer, and no step-2 question asks
  the user for a fact (assumed measure; see Proof).

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
