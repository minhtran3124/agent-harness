---
problem_type: knowledge
module: skills/feature-intake / rules/auto-correct-scope
tags: automation-readiness, standing-automation, hooks, ci-workflow, scheduled-loop, fail-silent, design-gate, enforce-by-consultation
severity: critical
applicable_when: A change adds a standing automation — a new hook (hooks/*), a CI / scheduled workflow, or a scheduled /loop — turning a recurring manual task into one that fires on its own. Consult before writing it, not after.
affects:
  - hooks/
  - .github/workflows/
supersedes: null
confidence: high
confirmed_at: 2026-07-17
---
## Applicable When

Before building any **standing automation** — a new hook under `hooks/*`, a CI or
scheduled workflow, or a scheduled `/loop` — i.e. whenever a recurring manual task is
about to become one that fires on its own. Consult at design time, before the automation
is written.

## Pattern

The risk-lane gate already forces `high-risk` for `hooks/*` / `settings.json` (high-blast
hard gate), so "how carefully do I build this" is covered. It does **not** ask two
*design* questions — and both have already cost this repo:

1. **Fail-safe & stop condition.** Does the automation degrade **safely and visibly** on the
   unexpected? It needs a finite retry, a fail-open boundary on advisory work (`… || true` on
   the *command*, not a try/except exception allowlist), and no silent pass. *"An automation
   that fails silently is dangerous."* The "advisory / never-blocks" enforcement bug shipped
   **twice** ([[bash-empty-array-and-jsonl-parsing-gotchas]]) because the boundary was an
   exception list, not a `|| true`; a prompt-decision automation failed silently deciding it
   could prompt ([[test-r-dev-tty-does-not-detect-missing-controlling-terminal]]).

2. **Warranted & objectively verifiable.** Does the task recur often enough to justify a
   *standing* cost (it fires every session / every commit), and can its output be checked
   **pass/fail objectively** with low false-alarm? A scanner that matches an ordinary English
   word in a test comment ([[risk-corroboration-scans-test-comments-for-auth-words]]) is a
   false-alarm tax paid on every commit.

## How to Use

When intake or design sees the diff **add** a hook, CI job, or scheduled loop, answer both
questions explicitly in `design.md` (or the SUMMARY `Rationale`) before writing the
automation. If either fails — no objective verify, no stop condition, or the task does not
really recur — prefer a **one-off script or manual step** over a standing automation.

This is **advisory (enforce-by-consultation)**: it rides the auto-loaded `critical-patterns.md`
channel and does not block a commit. Its effectiveness is the discipline of consulting
critical-patterns at planning time — the same soft contract every entry here relies on.

## Gotchas

- It does **not** replace the high-blast hard gate: `hooks/*` / `settings.json` still force
  `high-risk` lane independently ([[hooks-addition-is-high-risk-even-dormant]]). Readiness is
  the design layer *on top* ("should this automation exist / will it fail loud"), not a risk
  reclassification.
- The gate applies to itself: adding a hook to *enforce* readiness would have to pass
  readiness first (finite, fail-open, low false-alarm) — which is why this ships as a
  consulted pattern, not a new blocking hook.
