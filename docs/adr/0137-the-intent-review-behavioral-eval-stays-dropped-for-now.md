---
ticket: 528
stage: decision
status: needs-review
needs_review: true
confidence: high
decided_by: claude (528 decision; scope confirmed by the owner on the issue)
date: 2026-11-01
---

# 0137. The intent-review behavioral eval stays dropped for now

## Context

v5 measures nothing about intent-review. v4 had labeled fixtures with blind runs; #348 removed evals/ on purpose (/code-review replaces the in-house review chain), so bringing it back is a decision to revisit, not an oversight. A 2026-10 trial (21 + 49 calls on 7 v4 fixtures, reviewer without repo tools, claude-sonnet-5-5, medium effort) gave: the 2 target fixtures (intent-gap, excess-scope) were caught 10/10 each with lenient matching; the 5 control fixtures, which should say match, came back gaps found in 43 of 50 runs; and on context-rule-unread some runs list findings while the verdict is match. Nobody labeled the control findings, so it is unknown whether the reviewer is too strict or the fixtures hold real drift their truth files do not list. The figures come from the trial as described in issue #528. The fixtures and run logs are not in the repo, because #348 removed `evals/`; the 21 + 49 calls are all the calls of the trial, and the 43 of 50 counts the control-fixture runs only.

## Options

- Bring back a small intent-review eval now
- Record that the eval stays dropped for now, and open a follow-up that needs the owner's hand labels
- Drop it for good with no follow-up

## Decision

Do not bring the intent-review eval back in this ticket. Record that it stays dropped for now. The rebuild is the follow-up #537 (hand-label the 5 control fixtures, rewrite the control truth so it fits intent review, find why verdict and findings disagree on context-rule-unread, add fixtures until about 10 positive cases exist with the owner approving each answer key, run on the plugin intent-reviewer agent with repo tools and record the model and effort). Links: #348 removed the v4 evals on purpose. #213 covers a correctness-review eval; it is cross-linked only and is not merged with this decision.

## Why

The trial gave no usable rate: 7 fixtures, 2 targets, one model, no repo tools, and no hand labels on the control findings. Quoting a catch rate or a false-positive rate from it would be false precision. A rebuild without the owner's labels would repeat the trial. #348 removed the evals on purpose, so reverting that needs a reason the trial does not give.

## Consequences

intent-review stays unmeasured: there is no documented command that prints its catch rate and false-positive count. Nobody should quote the 10/10 or the 43/50 figure as a rate.

## How to reverse

Do the checklist in #537. The first step is the owner's: label the findings on the 5 control fixtures as true drift or false positive. When the eval exists, supersede this ADR with a new one that names it.
