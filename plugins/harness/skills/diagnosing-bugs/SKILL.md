---
name: diagnosing-bugs
description: Find and prove the root cause of a bug in six gated phases before any fix. Use when a ticket is an `Input-type: bug fix` that `intake` routes here, or run from `/harness:diagnosing-bugs`.
disable-model-invocation: true
allowed-tools: Read, Write, Edit, Grep, Glob, Agent, Task, Bash
---

# Diagnosing Bugs

## Redaction

Replace each secret with `<REDACTED>` before you show or write a command or an output.

## Scope

Every depth (S, M, L) runs all six phases. No "cause known" shortcut exists.

## Isolation

Create the isolation before Phase 1.
At depth S, run `git checkout -b fix/<slug>` only from a shared branch.
Otherwise keep the current branch.
At depth M and L, run `harness:using-git-worktrees`.
Do every probe, harness and fix edit there, never on a shared branch.

## Phases

Write `specs/<slug>/diagnosis.md` from `references/diagnosis-template.md`.
`references/phases.md` lists the techniques for Phases 1 to 4.

1. **Feedback loop.** Make one fast, deterministic command that an agent can run and that goes
   red on this bug. Run it as written, with no pipe, so its exit code shows the red.
   When a human must act, copy
   `${CLAUDE_SKILL_DIR}/scripts/hitl-loop.template.sh`. Ask the human to run it and paste the output.
   When no loop is possible, stop and ask the owner. List what you tried and need.
   Done when: `Loop:` holds the command and its redacted red output.
2. **Reproduce and minimise.** Delete one input element at a time. Add no probe or debug log.
   Done when: the loop shows the symptom that the user described, and each element in `Repro:` is necessary.
3. **Hypothesise.** Write three to five ranked hypotheses, `H1` to `H5`, each with a prediction,
   into `Hypotheses:`. Commit diagnosis.md before the first probe.
   Then post the list to the user. Do not wait for a reply.
   Done when: `Hypotheses:` holds three to five ranked entries, each with a prediction.
4. **Instrument.** Change one variable in each probe.
   Tag each debug log with a unique `[DEBUG-xxxx]` prefix. Do not commit a probe.
   When the probes refute every hypothesis, go back to Phase 3 with a new list.
   After a second full refutation, stop and ask the owner.
   After you confirm one hypothesis, delete every probe and throwaway harness.
   Done when: `Confirmed:` names one hypothesis that the probe evidence supports, and no probe stays in the working tree.

## Diagnosis review

Dispatch the `task-reviewer` to Read `${CLAUDE_SKILL_DIR}/references/diagnosis-review-prompt.md` first and follow it.
Give it the `diagnosis.md` path, not the prompt text.
Start Phase 5 only after `spec_verdict: pass` and `quality_verdict: approved`.
On any other verdict, revise `diagnosis.md` and review again.
After a second failure, stop and ask the owner.

## Phases 5 and 6

5. **Fix.** At depth S, write the red test at the `diagnosis.md` `Seam:`.
   Commit the red test. Then commit the fix.
   Report the red and green commands and their exit codes in your final message.
   When `diagnosis.md` has `Seam: none — <reason>`, write `Red test exempt: <reason>` in your final message.
   At depth M and L, continue with `harness:writing-plans` and `harness:implement`, with `diagnosis.md` as an input.
   Done when: the red test commit comes before the fix commit, or the final message has `Red test exempt: <reason>`.
6. **Cleanup.** Run the Phase 1 loop again.
   Search for `[DEBUG-` in the fix diff and in the working tree, untracked files included.
   Delete each tagged log or throwaway harness that you find.
   Name the confirmed hypothesis in the commit message and in the final message.
   Done when: the loop is green, the search finds no tag, and both texts name the confirmed hypothesis.
