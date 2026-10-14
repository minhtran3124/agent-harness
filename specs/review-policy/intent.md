# Intent: One review policy, and plain wording across the review skills

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

Each review pass carries its own severity scale and its own "do not report" list: task review
uses Critical / Important / Minor, correctness review uses P0–P3 plus a score threshold, and
intent review uses gap / drift / excess. Nothing says which findings are worth a fix round and
which are nits, caps the nits, or excludes generated files and what CI already enforces. Play 9
of the SDLC playbook keeps that in one `REVIEW.md`-style policy (research note §6, E1).

## Proposed outcome

A review policy that the review skills read, which defines:

- what counts as Important versus Nit, mapped onto each existing scale rather than replacing it (assumed);
- how nits are reported, so they never trigger a fix round (see Q3);
- a do-not-report list, including generated files and anything CI already enforces;
- a label on each finding that says what it was checked against: the task reviewer labels against `PLAN.md` SC-n, intent review against the SUMMARY Intent, and correctness review is exempt because it is plan-blind.

The policy lives in `rules/review-policy.md`, path-scoped, and each review prompt reads it explicitly.

Every review agent and skill in the workflow is also reviewed and rewritten so its wording is
simple and easy to understand, following the Opus 5.5 prompt standard this repo already uses
(`rules/behavior.md` §4–§5 and the `opus-5-5-prompt-audit` decisions: plain complete sentences,
no invented shorthand, lean prompts that trust the model). The files in scope (assumed):

- `agents/reviewer.md`, `agents/task-reviewer.md`;
- `skills/correctness-review/` (SKILL, finder and scorer prompts, `prompts/shared.md`, the six angle prompts);
- `skills/intent-review/` (SKILL, reviewer prompt);
- `skills/subagent-driven-development/task-reviewer-prompt.md` and `references/review-chain.md`;
- `skills/context-propagation-audit/SKILL.md`.

## Affected users and systems

- Review passes: the task reviewer (SDD), correctness review (finders and scorer), and intent review (assumed).
- Their dispatch prompts and `agents/` definitions, which must deliver the policy to each fresh reviewer context (assumed).

## Constraints

- Correctness review stays blind to `PLAN.md`, and intent review stays blind to plan prose; the policy must not break either oracle's independence (assumed).
- Existing severity scales, the scorer threshold, and blocking rules keep their meaning (assumed).
- Each reviewer receives the policy by an explicit Read or a complete pasted copy, proved by the context-propagation audit (assumed).
- Prompts stay lean: skill word budgets still pass `scripts/audit_skill_prompts.py` (assumed).
- The rewrite changes wording, not behavior: each reviewer keeps its oracle, inputs, output schema, finding categories, and blocking rules (assumed).

## Out of scope

- `/code-review` and the in-PR review loop (H4) (assumed).
- Changing which findings block a merge (assumed).

## Open questions

- Q3. The nit cap conflicts with `opus-5-5-prompt-audit` decision 2 (2026-09-29), which removed the review caps in the finder and the task reviewer because the scorer is the precision stage. Proposed default: no count cap on findings; instead the policy says Nit findings are reported in one batched, non-blocking list (assumed).

## What success looks like

- Each review prompt names the policy file and has a test or lint that fails if the reference is removed (assumed).
- The context-propagation audit passes for every reviewer context (assumed).
- The total word count of the in-scope review files does not grow, apart from the new policy file (assumed).
- `bash scripts/run-tests.sh` stays green (assumed).

## Original request

"làm E1 di" — E1 in `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §6:

| **E1** | **Write a review policy (`REVIEW.md`-style) for the review skills**: what counts as Important vs Nit, a nit cap, a do-not-report list (generated files, anything CI already enforces), and a mandatory "compliance vs PLAN.md SC-n + SUMMARY Intent" pass label on each finding | Play 9 | new `REVIEW.md` or a section in `skills/correctness-review/` | normal (workflow-engine → audit) |

Reply to the draft (2026-10-11):

"1. đồng ý
2. đồng ý
3. hãy review lại toàn bộ agent/skills liên quan đến review trong workflow hiện tại (correct review, intent review, ...) và đảm bảo câu chữ đơn giản dễ hiểu, theo chuẩn của opus5.5"
