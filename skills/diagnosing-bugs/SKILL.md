---
name: diagnosing-bugs
description: Find and prove the root cause of a bug in six gated phases before any fix. Runs for an `Input-type: bug fix` that `feature-intake` routes here, or from `/diagnosing-bugs`.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Agent, Task, Bash
---

# Diagnosing Bugs — prove the cause before the fix

## Redaction

Replace each secret with `<REDACTED>` before you show or write a command or an output.

## Scope

Every lane runs all six phases. No "cause known" shortcut exists.

## Isolation

Create the lane's isolation before Phase 1. On the tiny lane, run `git checkout -b fix/<slug>`.
On the normal and high-risk lanes, run `using-git-worktrees`.
Do every probe, harness and fix edit there, never on a shared branch.

## Phases

Write `specs/<slug>/diagnosis.md` from `references/diagnosis-template.md`.
`references/phases.md` lists the techniques for Phases 1 to 4.

1. **Feedback loop.** Make one fast, deterministic command that an agent can run and that goes
   red on this bug. Run it at least once. When a human must act, copy
   `skills/diagnosing-bugs/scripts/hitl-loop.template.sh` and run the copy with `bash`.
   When no loop is possible, write an `ESCALATIONS.md` block with `decision: pending`.
   List what you tried and what you need. Then stop.
   Done when: `Loop:` holds the command and its redacted red output.
2. **Reproduce and minimise.** Delete one input element at a time.
   Done when: the loop shows the symptom that the user described, and each element in `Repro:` is necessary.
3. **Hypothesise.** Post three to five ranked hypotheses, `H1` to `H5`, as reply text
   before the first probe. Give each hypothesis a prediction.
   Continue on your own ranking. Do not wait for a reply.
   Done when: `Hypotheses:` holds three to five ranked entries, each with a prediction.
4. **Instrument.** Start no probe before you post the Phase 3 list.
   Map each probe to one prediction. Change one variable in each probe.
   Tag each debug log with a unique `[DEBUG-xxxx]` prefix. Do not commit a probe.
   When the probes refute every hypothesis, go back to Phase 3 with a new list.
   A second full refutation writes an `ESCALATIONS.md` block with `decision: pending` and stops.
   After you confirm one hypothesis, delete every probe and throwaway harness.
   Commit `specs/<slug>/diagnosis.md`.
   Done when: `Confirmed:` names one hypothesis that the probe evidence supports, and no probe stays in the working tree.

## Diagnosis review

Dispatch the `task-reviewer` agent with the path of `references/diagnosis-review-prompt.md`, not its text.
Give it the `diagnosis.md` path and the `SUMMARY.md` path.
Start Phase 5 only after `spec_verdict: pass` and `quality_verdict: approved`.
When the review fails, revise `diagnosis.md` and review again.
A second failure writes an `ESCALATIONS.md` block with `decision: pending` and stops.

## Phases 5 and 6

5. **Fix.** On the tiny lane, write the red test at the `diagnosis.md` `Seam:`.
   Record the `red` and `green` rows that `rules/auto-correct-scope.md` names.
   When `diagnosis.md` has `Seam: none — <reason>`, record a finding in `SUMMARY.md`.
   Then write `Red test exempt: <reason>`.
   On the normal and high-risk lanes, continue the lane route with `diagnosis.md` as an input.
   The fix task's `Seams:` copies the `Seam:` line.
   Done when: the red test commit comes before the fix commit, or `SUMMARY.md` has `Red test exempt: <reason>`.
6. **Cleanup.** The session that completed the fix does this phase. Run the Phase 1 loop again.
   Search for `[DEBUG-` in the fix diff and in the working tree, untracked files included.
   Delete each tagged log or throwaway harness that you find.
   Name the confirmed hypothesis in the commit message and in SUMMARY `Rationale`.
   Done when: the loop is green, the search finds no tag, and both texts name the confirmed hypothesis.
