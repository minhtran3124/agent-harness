---
problem_type: failure
module: harness
tags: review-chain, subagent-dispatch, no-report, review-receipt, independence, silent-degradation, evidence-over-assertion
severity: critical
applicable_when: A dispatched reviewer subagent (correctness / intent / context-propagation) returns no findings text — it went idle, errored, or the channel dropped — and you are about to continue the ship chain.
affects:
  - skills/subagent-driven-development/SKILL.md
  - templates/REVIEW-RECEIPT.template.json
  - scripts/check_review_receipt.py
supersedes: null
confidence: high
confirmed_at: 2026-07-27
---
## Applicable When

A reviewer subagent finishes without delivering its report, and the controller has to decide what that
means. Also whenever you write `.review-receipt.json` for reviews you did not run independently.

## Symptom

Four reviewers dispatched in one message (`reviewer` agent type, model different from the implementer)
all went **idle without returning findings text**. Follow-up `SendMessage` requests to three of them
produced another idle notification and no report. `TaskList` showed no tasks. Nothing errored — the
chain simply had no output to act on.

## Wrong Approach

Two tempting readings, both wrong:

1. **Treat silence as a pass.** No findings returned looks like no findings found. It is the absence of
   a review, not the result of one — `not_observed != absent` (`rules/behavior.md` §1).
2. **Substitute a main-thread self-review and write a normal receipt.** The receipt's purpose is to
   prove reviews ran against the shipped code; its schema (`type`, `reviewer`, `result`,
   `blocking_open`) has **no field for independence**, so a controller-run pass and an independent one
   serialize identically. Gate 0 then passes on a receipt that overstates what happened.

## Why It Failed

`skills/subagent-driven-development/SKILL.md` specifies dispatch and the fix-loop but never the
no-report case, so the controller is left choosing silently between blocking forever and degrading the
gate. And because the receipt cannot express "reviewed, but not independently", the degradation leaves
no trace: the ensemble-diversity requirement the chain depends on disappears without a record.

The practical proof that independence matters: in this session the inline correctness pass verified that
`run_state.py init` was idempotent on an existing run and stopped there — it never tested
`init`-then-`implementing` on a *fresh* one, which is where the real defect was. An external reviewer
found it immediately. Idempotency was the wrong question, and only a different reading frame asked a
different one.

## Correct Approach

- **A no-report dispatch is a failed review, not a passing one.** Re-dispatch, or run the pass in the
  controller and say so explicitly.
- **Record the degradation in the artifact, not just the chat.** Until the schema has a field, write it
  into the `reviewer` string verbatim (`"main-session … (dispatched subagents returned no report; NOT
  independent)"`) and into `SUMMARY.md` `### Review`. A reader must be able to tell from the receipt
  alone that ensemble diversity was absent.
- **Get independence from outside the harness when the local chain cannot supply it.** On a
  workflow-engine diff, `finishing-a-development-branch` already recommends an external pass. In this
  session that external reviewer produced 19 findings across 15 rounds, of which 17 were real — none of
  them local logic bugs, all relationships with code outside the file under review.

## Guardrail

`proposed:` add a required `independent: true|false` to each receipt entry
(`templates/REVIEW-RECEIPT.template.json`), and have `scripts/check_review_receipt.py` fail a
`normal`/`high-risk` push whose `correctness` or `intent` entry is `independent: false` unless an
explicit override reason is recorded — so a degraded chain blocks or is consciously accepted, never
silently shipped.

## Related

- `docs/solutions/harness/unverified-premise-propagates-through-plan-anchored-reviews.md` — the sibling
  failure: reviews that ran but shared one false premise.
- `docs/solutions/harness/prose-encoded-state-logic-accrues-contradiction-chains.md` — what the external
  reviewer kept finding once it did run.
