---
problem_type: knowledge
module: harness
tags: workflow-as-code, prose-vs-code, state-machine, skill-authoring, contradiction-chain, exhaustive-enumeration, fsm-consumers
severity: critical
applicable_when: A SKILL.md section is about to branch on more than a couple of states of a real state machine (run-state FSM, plan lifecycle, CI status) — decide the medium before writing the third branch.
affects:
  - skills/subagent-driven-development/SKILL.md
  - runtime/test_run_state.py
supersedes: null
confidence: high
confirmed_at: 2026-07-27
---
## Applicable When

Writing or extending a skill step that reads a state machine and decides what to do per state. The
signal to stop and reconsider the medium: you are copying a transition table into markdown, or writing a
test that compares your copy against the original.

## Pattern

**State logic written as prose accrues contradiction chains: each correction is individually right and
creates the next gap, because the preconditions live in the engine and prose never forces you to
enumerate them.**

Measured on one PR (#173, resume path in `subagent-driven-development`): 19 findings over 15 external
review rounds, of which **6 of the last 8 were defects in prose that PR had just added** — not in what
the feature did. Four formed a single chain:

| Round | Defect introduced by the previous fix |
|---|---|
| 12 | interrupt rows had no route forward once the blocker cleared |
| 13 | the new "transition back to `from_state`" fails for 3 of 11 states — a waiting target needs `--waiting-on`, which the interrupt event overwrote |
| 14 | the new "route forward per that state's row" pointed at a row that says only *STOP and report* — circular |
| 15 | the new successor table routes to `awaiting_review`, itself a waiting state, so it needs its own `--waiting-on` — round 13's defect, one step later |

Two of those fixes ended by **copying `FORWARD_TRANSITIONS` into markdown and adding a test that
compares the copy to the original.** When a test exists to detect that your duplicate drifted from the
source, the duplicate is the bug.

## How to Use

Three graded responses, cheapest first:

1. **Enumerate exhaustively, never by default.** If prose must branch on states, cover *all* of them with
   an explicit verdict — `queued` … `shipped`, 16 in this FSM — and never leave "anything else" implied.
   The exhaustive sweep here immediately classified four states no reviewer had raised
   (`awaiting_confirmation`, `awaiting_ci`, `awaiting_review`, `ready_to_merge`).
2. **Assert executability, not wording.** A guard that checks the prose *names* a state passes while the
   named route cannot actually be taken. Upgrade it to run each documented transition against the real
   engine, supplying whatever that target class demands, and to assert the rejection case too so it
   cannot pass vacuously.
3. **Extract to a script once the branch count outgrows the medium.** The threshold reached here: a
   16-state table, five stop conditions, three exit-code branches and four guards that string-match the
   prose. That is a function with a handful of branches, spread across paragraphs.

## Gotchas

- **Exhaustive coverage of states is not coverage of edges.** Round 8 found `queued`/`investigating`
  classified as "proceed" while neither can reach `implementing` in one legal hop. Check each verdict
  against the transition graph, not just against the state list.
- **A non-fatal checkpoint hides every one of these.** All four chain links were invisible because the
  prescribed call ends in `|| true`: an illegal transition exits 2, the guard swallows it, and the run
  keeps a stale state while work proceeds. Any `|| true` in a skill is a place where prose defects cannot
  announce themselves.
- **The reviewer that finds these reads the file as code.** Every one of the 17 confirmed findings was a
  relationship with something *outside* the file under review — a rule that writes `STATE.md`, a hook's
  arming condition, a CLI's exit-code contract, an append-then-project write order. Model diversity does
  not produce that; a different reading frame does.

## Related

- `docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md` — why the text-anchored
  guards here needed mutation checks.
- `docs/solutions/harness/automation-readiness.md` — the companion decision gate for *adding* mechanism.
