---
problem_type: knowledge
module: skills/subagent-driven-development/task-reviewer-prompt.md (and any reviewer or scorer prompt)
tags: review-oracle, reviewer-prompt, canary, historical-replay, model-judgement, blind-run, fixture-fitted-tests
severity: standard
applicable_when: You change what a reviewer prompt checks (task reviewer, correctness finder or scorer, intent reviewer) and need evidence that the reviewer now flags the target defect, not only that the prompt text holds the new words.
affects:
  - skills/subagent-driven-development/task-reviewer-prompt.md
  - specs/gh-312-test-seams/canary.md
supersedes: null
confidence: high
confirmed_at: 2026-10-16
---
## Applicable When

You change what a reviewer prompt checks, and you need evidence that the reviewer now flags the
target defect. A phrase pin proves only that the words are present.

## Pattern

Use two runs of the real reviewer agent with the real prompt.

1. **Canary (the gate).** Write a small fixture: a brief, an implementer report and a review
   package (a hand-written diff is enough). Plant each target defect once, and add clean controls
   beside them. Do not tell the reviewer which parts are bad. The run passes when every planted
   defect gets the expected severity and no control gets a finding.
2. **Historical replay (evidence).** Take a recorded case where the old review approved and a
   later review found the defect. Rebuild its brief and package from the original commits, add
   only what the new rule needs (for gh-312, the `Seams:` line), and run the new reviewer on the
   original diff. Compare its findings with the later review's findings, row by row. Record the
   result as it is. Do not make it a gate.

In gh-312 the canary caught both planted tests (off-seam, expected value computed by the code
under test). It also found a real bug that the circular test hid. The replay of gh-175 Task 2.1
returned `needs_fixes`, where the original per-task review approved. It named the synthetic-only
fixtures (seam step 3) and the per-entry SHA association, which match gh-175 correctness findings
[A/B] and [C]. It did not find the other nine code defects, which the seam check does not target.

## How to Use

- Keep the canary fixture under `specs/<slug>/canary/` and the record in `specs/<slug>/canary.md`,
  with each reviewer output in a fenced block. A plan check can then be
  `grep -q "^Canary result: pass$" specs/<slug>/canary.md`.
- Build briefs and packages with the same scripts that SDD uses (`task_brief.py`,
  `review_package.py`), so the run sees what a real dispatch sees.
- Set a failure budget before the run (gh-312: two failed runs, then escalate). One sample can
  pass by chance, so state in `### Not auto-verified` that one canary run is one sample.
- In the replay record, say which tree the reviewer could search. A replay against today's tree
  sees more real inputs than existed at the time.

## Gotchas

- Plant defects in the reviewer's exact terms. "Copied from the output" and "computed by the code
  under test" are different words. Test the subtler one; the canary is where a narrow wording
  shows up.
- Do not pre-label findings in the fixture (no `# bad` comments). The reviewer reads the diff.

## Related

- docs/solutions/harness/skill-eval-blind-run-scoring.md
- docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md
- docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md
