# skill-prompt-refactor — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-quality-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: orchestrator (Task 7.1 controlled A/B)
- date: 2026-07-29
- trigger: system-redefinition
- question: SC-2 requires 192/192 activation cases to pass; the completed A/B measures 162/192 for the candidate and 152/192 for the pre-refactor baseline — do we revise SC-2 to a non-regression bar, or hold the 100% bar and keep iterating?
- context: Task 7.1 is otherwise complete. Every suite now has full first-run coverage for both arms (activation 192, behavior 36, end-to-end 5 per arm), the review-chain and context-boundary protocols are run and recorded, and the full suite is green. SC-3 and SC-6 pass. Only SC-2 and SC-9 fail, and both fail against a bar the pre-refactor baseline also fails. Task 8.1 (final proof, deployment, plan `shipped`) is blocked on this decision.
- evidence:
  - Candidate is **better** than baseline on activation: 162 vs 152 pass, 11 improvements vs 1 regression, **zero** new false positives, and it removed the baseline's only false positive. `context-propagation-audit` should-trigger misses fell 8 → 2.
  - The 100% bar is not attainable for either arm on the current corpus. Several misses are fixture/probe artifacts shared by both arms — most clearly `visual-planner`, missed 8/8 in **both** arms because the corpus positive ("Render this PLAN.md as HTML…") predates `hooks/render-plan-on-write.sh`, so "no skill needed, the hook already rendered it" is the substantively correct answer.
  - The single SC-9 regression is `intent-review-trigger-4`, baseline `pass` → candidate `blocked`: the candidate returned no TRIGGER/NO-TRIGGER decision at all, so no activation judgement was observed. It is a lost observation, not an observed wrong answer.
  - Full results: `evals/skills/prompt-refactor/results/candidate.md`.
- options:
  - A) **Revise SC-2 to a non-regression bar** (candidate activation pass-rate ≥ baseline, and no new false positives) and re-ground the stale fixtures (`visual-planner` positives, `feature-intake`/`xia2` probe wording) in a follow-up. Consequence: SC-2 measures what the refactor is responsible for; the plan can ship on evidence that is already collected and favourable. Cost: the absolute activation quality bar is deferred to a separate piece of work, and this run's 30 candidate misses stay on the record as known-unfixed.
  - B) **Hold the 100% bar.** Iterate on skill descriptions and re-run affected cases as new recorded attempts until 192/192. Consequence: the strongest possible activation guarantee. Cost: substantial further live-eval spend, and it is not clear the bar is reachable at all — the `visual-planner` cases would require either a description change that contradicts the render hook, or a fixture change, which is option A's work under a different name.
  - C) **Split**: revise SC-2 to a non-regression bar now (as in A), and additionally require the corpus fixture re-grounding to land *before* ship rather than as a follow-up. Consequence: slower than A, but the plan does not ship citing a criterion whose fixtures are known stale.
- separate sub-decision (SC-9): whether `intent-review-trigger-4` should be treated as a genuine regression or invalidated as a failed collection via `scripts/invalidate_skill_eval_collection.py`, the way the earlier response-collection failures were. Recommend **treating it as a real regression and leaving it recorded** unless a human decides the empty response is a transport failure — the first-run honesty rule says an inconvenient result is not re-run until it improves.
- default_if_no_response: BLOCK
- decision: **A** — revise SC-2 to a non-regression bar (candidate activation pass-rate ≥ baseline, and no new false positives). Fixture re-grounding (`visual-planner` positives, `feature-intake`/`xia2` probe wording, `soft-delete-filter`'s dead answer key) and the corpus case-versioning it requires are filed as separate work, not folded into this plan. Sub-decision on SC-9: **fix the scorer** — `pass → blocked` reports as unmeasured coverage rather than a regression, matching the safety-critical check that already excludes `blocked` and this repo's `not_observed != absent` rule. The first-run record for `intent-review-trigger-4` stays exactly as observed and is not re-run.
- decided_by: Minh Tran
- decided_at: 2026-07-29
