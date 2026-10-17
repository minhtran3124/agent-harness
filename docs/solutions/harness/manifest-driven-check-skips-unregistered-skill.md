---
problem_type: failure
module: harness
tags: [new-skill, harness-manifest, registration, task-verify, vacuous-check, prompt-audit, tool-conformance, green-is-not-correct, plan-ordering]
severity: standard
applicable_when: You plan or verify a task that adds a new skills/<name>/SKILL.md, and its Verify runs a manifest-driven check (audit_skill_prompts.py, check_skill_tool_conformance.py, check_frontmatter_contract.py) before the skill is in harness-manifest.json.
affects:
  - scripts/audit_skill_prompts.py
  - scripts/check_skill_tool_conformance.py
  - scripts/check_frontmatter_contract.py
  - scripts/check_manifest.py
supersedes: null
confidence: high
confirmed_at: 2026-10-16
---
## Applicable When

You plan or verify a task that adds a new `skills/<name>/SKILL.md`. The task's Verify runs a
check that reads the skill list from `harness-manifest.json`: the word-ceiling audit, the
`allowed-tools` conformance check, or the frontmatter contract. A later task registers the
skill.

## Symptom

The task's Verify exits 0, but the check never read the new file. In the onboarding-skill run,
Task 1.2 wrote `skills/onboarding/SKILL.md` with `python3 scripts/audit_skill_prompts.py` as
its Verify. The audit passed with `problems: []` while the file was not registered. Task 2.1
registered the skill later. Only then did the audit and the conformance check read the file. At
that point the file was at 592 of the 600-word ceiling, with no room left for review fixes.

## Wrong Approach

The plan used a manifest-driven check as the Verify of the task that writes the skill. It put
the registration in a later wave. The plan treated "the check exits 0" as "the check passed on
this file".

## Why It Failed

These checks iterate the manifest `skills` list, not the files on disk
(`scripts/audit_skill_prompts.py` reads the list from the manifest). A skill that is missing
from the list is out of scope, so the check has nothing to fail on. The exit code is honest about
the files that it read. It says nothing about a file that it did not read.

## Correct Approach

Use one of these three methods:

- Put the registration (`harness-manifest.json` `skills`) in the same task as the new
  `SKILL.md`, so the task's Verify reads the file.
- Add `python3 scripts/check_manifest.py` to the Verify of the task that writes the skill. Its
  section A fails when a `skills/<name>/SKILL.md` on disk is missing from the manifest, so the
  vacuous pass becomes a visible failure.
- If the registration must come later, run the check against a copied root whose manifest lists
  the skill. Record that in the task report. The onboarding-skill implementer did this on a
  scratch copy and reported the 592-word count early.

## Guardrail

existing: `scripts/check_manifest.py` (section A, manifest against disk) fails on an unregistered
on-disk skill. The gap was a plan that left it out of the task's Verify. It was not a missing
check.

## Related

- docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md
- docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md
