---
slug: correctness-review-angles
status: active
owner: Minh Tran
created: 2026-07-13
---

# Rewrite the correctness finder as parallel angles; delete FIND-B

## 1. Motivation

Two facts, both established by measurement rather than argument:

**(a) The finder has a structural blind spot.** `/correctness-review`'s finder is one agent
reading one bug-class checklist. Claude Code's built-in `/code-review` instead runs several
independent finders, each with a different *method* of looking. Two of its methods have no
equivalent in our checklist, because they are not bug classes at all — they are search
procedures:

- **read the enclosing function of every changed hunk**, not only the changed lines;
- **for every deleted line, name the behavior it enforced and find where the new code
  re-establishes it.**

This is not hypothetical. During the review of PR #51 (2026-07-13), the highest-value finding —
three live abort paths in `scripts/harness-status.sh` — sat on lines the diff did not modify.
Our finder's checklist gives no instruction that would reach them.

**(b) FIND-B does not earn its cost.** FIND-B was added to buy "ensemble diversity: a different
engine, different angles, different blind spots". Parallel angles inside our own finder buy the
same angle diversity at roughly one tenth the token cost, with no output adapter, no
recall-biased verdict to quarantine, and no invocation problem. FIND-B's remaining justification
would be *model*-level diversity, which is unmeasured. We do not ship unmeasured stages.

## 2. Non-goals

- **Not adopting `/code-review`'s verdict ladder.** Its verify stage is recall-biased by its own
  label. SCORE (independent, 0–100, threshold 80) remains the precision gate, unchanged.
- **Not adopting its cleanup angles** (Reuse, Simplification, Efficiency, Conventions). This
  skill reports runtime bugs only. Cleanup belongs to `/code-review` standalone and the per-task
  quality reviewer.
- **Not widening SCORE.** A finding on a line the diff did not modify still scores **0**. See
  §4, Task 1.2 — such findings are reported as *advisory*, never routed to the fix-loop.
- **Not building an automated benchmark runner.** The protocol stays manual per
  `benchmarks/review-chain/README.md`.

## 3. Success Criteria

1. The finder dispatches **six angles in parallel**; each angle returns at most 6 candidates, and
   every candidate carries a concrete trigger (input/state) and the wrong outcome it produces.
2. **FIND-B is gone** from every file. No dangling references; the doc-truth lint passes.
3. A finding on an unmodified line is **reported as advisory**, not silently dropped and not
   routed to the fix-loop.
4. **Benchmark, all 5 fixtures, one scored run, recorded before merge.** Recall must not regress
   against `results/2026-06-baseline.md` (3/3 on the correctness fixtures; CLEAN on the two
   intent fixtures). Hard gate: **a recall regression stops the change** — it does not get
   re-run until it passes (`README.md` honesty rule).
5. `correctness-reviewer-prompt.md` is literal throughout: every instruction states plainly what
   to do and what to report. No metaphor, no allusion, no figurative language.

## 4. Tasks

### Task 1.1 — Rewrite the finder as six parallel angles

```xml
<task id="1.1" wave="1">
  <files>skills/correctness-review/correctness-reviewer-prompt.md</files>
  <action>Replace the single-finder bug-class hunt with six angles, dispatched in parallel, one subagent each (subagent_type: reviewer). Each angle returns at most 6 candidates. Angles: (A) scan every changed hunk line by line, then read the enclosing function — a bug on an unmodified line inside a changed function IS in scope and must be reported, marked `unmodified-line`; (B) removed-behavior auditor — for every line the diff deletes or replaces, state the behavior or guard it enforced, then locate where the new code re-establishes it; if it is not re-established, report it; (C) cross-file tracer — for each changed function, grep its callers and callees and check for a broken precondition, changed return shape, new exception, or new ordering requirement; (D) stack-pitfall specialist — the existing bug-class list (None/async/DB/auth/concurrency/contract/validation), demoted from "the whole finder" to one angle, and stated as adaptable to the diff's actual language; (E) altitude/boundary — the existing altitude pass, unchanged in substance; (F) compound read-back — read docs/solutions/critical-patterns.md and the failure-track entries, and check the diff against each applicable past defect by name. EVERY angle, not just E, requires a concrete trigger: name the input or state and the wrong outcome it produces. No trigger, no finding. Language must be literal: state the instruction directly. Remove every metaphor and figurative phrase from the file ("buy its way in", "bandaid", "where the crash paths hide", "checklist not a blindfold", and any others).</action>
  <verify>bash scripts/run-tests.sh</verify>
  <done>Six angles specified with explicit dispatch, per-angle candidate cap, and a mandatory trigger field. No figurative language remains. Suite green.</done>
</task>
```

### Task 1.2 — Scorer: dedup by location, and route unmodified-line findings to advisory

```xml
<task id="1.2" wave="1">
  <files>skills/correctness-review/correctness-scorer-prompt.md</files>
  <action>Two changes. (1) Dedup before scoring: when two or more angles report the same (file, line), score that location ONCE. Agreement between angles is provenance, not evidence — record which angles reported it, and do not raise the score because more than one did. (2) Make the unmodified-line rule explicit and its consequence explicit. Keep the score at 0 for a finding on a line the diff did not modify — that rule is unchanged. Then state plainly what happens next, because the current prompt leaves it implicit: a score of 0 does NOT mean the finding is discarded. It means the finding does not enter the fix-loop. It is recorded as `advisory` (SUMMARY.md → Advisory Findings when a slug is in play; reported inline otherwise), because a pre-existing bug is real code the author did not touch, and auto-fixing it on a feature branch violates surgical-change discipline. Reference the PR #51 review as the worked example: three real aborts on unmodified lines, correctly kept out of the fix-loop, correctly surfaced to the human.</action>
  <verify>bash scripts/run-tests.sh</verify>
  <done>Scorer dedups by location, states the 0-rule, and states the advisory consequence explicitly. Suite green.</done>
</task>
```

### Task 2.1 — SKILL.md: new pipeline, FIND-B deleted

```xml
<task id="2.1" wave="2">
  <files>skills/correctness-review/SKILL.md, skills/correctness-review/find-b-prompt.md</files>
  <action>Delete find-b-prompt.md entirely. In SKILL.md: remove the FIND-B step, the FIND-B callouts (controller-invokes, lane-source), and the FIND-B row from the Prompt Templates list. Rewrite the pipeline header as FIND (6 angles) → dedup → SCORE → THRESHOLD(80) → classify → fix-loop. Keep the "Why SCORE survives" callout — it is still true and is now the reason we did NOT adopt /code-review's verdict ladder — but restate it as a design rationale rather than a comparison to a stage we no longer run. In "Relationship to other review skills", restate /code-review as a SIBLING again (it is no longer a component): usable standalone for a cleanup-and-correctness sweep; note that its altitude lens and its angle method were adopted here, and that the engine swap was measured and rejected (cite the two results files).</action>
  <verify>bash scripts/run-tests.sh</verify>
  <done>find-b-prompt.md gone; no FIND-B reference remains in SKILL.md; doc-truth lint resolves every path. Suite green.</done>
</task>
```

### Task 2.2 — Downstream docs: drop FIND-B

```xml
<task id="2.2" wave="2">
  <files>skills/subagent-driven-development/SKILL.md, skills/README.md</files>
  <action>In subagent-driven-development/SKILL.md: remove FIND-B from the pipeline paraphrase and delete the "Pass the lane" paragraph (FIND-B was the only thing gated on it). Trim the paraphrase to name the stages and defer detail to skills/correctness-review/SKILL.md — it drifted once already and restating detail is what caused that. Restore the "Relationship to /code-review" paragraph to the sibling framing (compound, do not replace), which is true again. In skills/README.md: delete the FIND-B row from Integration Evidence Tiers (the integration no longer exists) and update the /correctness-review row to describe the angle-based finder.</action>
  <verify>bash scripts/run-tests.sh</verify>
  <done>No FIND-B reference anywhere in the repo (grep -ri "find-b" returns only benchmark result files, which are historical records and stay). Suite green.</done>
</task>
```

### Task 3.1 — Benchmark the new chain (the proof gate)

```xml
<task id="3.1" wave="3">
  <files>benchmarks/review-chain/results/2026-07-13-angles.md</files>
  <action>Run the manual protocol from benchmarks/review-chain/README.md against the rewritten chain, all 5 fixtures, one throwaway worktree each, blind (reviewer forbidden to read benchmarks/, docs/solutions/, specs/; greps pathspec-scoped). Score each pass against truth.md as caught / caught-wrong-reason / missed / false-positive. Record: catch rate, hard false-positive count, approximate token cost per pass. Compare against results/2026-06-baseline.md (3/3 correctness, CLEAN on the two intent fixtures, 0 hard FPs) and against results/2026-07-13-altitude-pass.md (3/3, 3 hard FPs, unattributed). Report the numbers as measured. HONESTY RULE: this is ONE scored run — do not re-run a fixture until it passes. If recall regresses, STOP and escalate; do not tune the prompt and re-measure in the same breath. Also state explicitly what this run does NOT measure.</action>
  <verify>test -f benchmarks/review-chain/results/2026-07-13-angles.md &amp;&amp; grep -qc "missing-await\|none-deref\|soft-delete\|excess-scope\|intent-gap" benchmarks/review-chain/results/2026-07-13-angles.md</verify>
  <done>Results file records all 5 fixtures with verdicts, catch rate, FP count, token cost, and a comparison against both prior runs. Recall did not regress, or the change is stopped and escalated.</done>
</task>
```

## 5. Risks

| Risk | Mitigation |
|---|---|
| **Six parallel angles raise the false-positive rate** — more finders, more noise. The altitude round-1 regression is the precedent. | Every angle carries the mandatory-trigger gate that fixed round-1. SCORE + threshold-80 is unchanged and is the precision gate. The benchmark measures FP count directly; a rise is a stop condition, not a footnote. |
| **Angle A reports pre-existing bugs and floods the report.** | They score 0 and land in Advisory, never the fix-loop. If Advisory becomes noisy in practice, that is a tuning signal, not a correctness failure. |
| **Recall regresses** — the checklist is demoted to one of six angles and something it used to catch is now missed. | This is the primary thing the benchmark tests. A regression is a hard stop (Success Criteria 4). |
| **Cost rises** — six subagents instead of one. | Still far below FIND-B's 10–15×, which this change deletes. Net cost should fall. Record measured tokens in the results file; do not assert the saving without measuring it. |
| **The three residual FPs from the altitude run are still unattributed.** This change alters the finder again, so the confound deepens. | State it in the results file. Do not claim this change fixed them, and do not claim it did not. `not_observed != absent`. |

## 6. Status Log

- 2026-07-13 — Plan written. Design decided by the user: keep SCORE=0 for unmodified lines (advisory, not fix-loop); delete FIND-B; benchmark inside this change; prompt must be literal.
