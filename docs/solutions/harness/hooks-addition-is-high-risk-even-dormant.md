---
problem_type: knowledge
module: hooks/commit-workflow
tags: hooks, high-blast, risk-corroboration, dormant-hook, lane-classification, workflow
severity: standard
applicable_when: Use this when a change adds or edits any file under hooks/ — including a dormant hook not yet registered in settings.json — because the corroboration gate keys on path, not on whether the hook is wired.
affects:
  - hooks/
  - templates/SUMMARY.template.md
supersedes: null
confidence: high
confirmed_at: 2026-07-17
---
## Applicable When
Use this when a change adds or edits any file under `hooks/` — including a dormant hook not yet registered in `settings.json` — because the corroboration gate keys on path, not on whether the hook is wired.

## Pattern
Treat any addition or edit under `hooks/` as **high-risk up front**, even a dormant, unregistered hook. `hooks/risk-corroboration.sh` matches the staged diff against the `^hooks/` high-blast regex; it does not inspect whether the hook is wired into `settings.json`. If the declared lane is below `high-risk`, the commit is blocked.

## How to Use
Before committing a new or changed file under `hooks/`, write `specs/<slug>/SUMMARY.md` declaring `Lane: high-risk` with non-placeholder `### Verify` and `### Rollback` blocks. Stage that SUMMARY in the same commit. The corroboration hook resolves the lane from a staged SUMMARY first; with `high-risk` declared and the evidence blocks present, the commit passes on the first attempt instead of bouncing on the gate. Validate the new SUMMARY up front with `python scripts/verify_summary.py --lane <slug>`, then re-run its proof with `python scripts/verify_summary.py --check <slug>`.

## Gotchas
Dormancy does not exempt a hook from the gate: a hook present on disk but absent from `settings.json` still trips `^hooks/`. The high-risk SUMMARY (with Verify + Rollback) must exist **before** the commit, not after the gate rejects it. This is the gate working as designed — it caught an author under-classifying a dormant-hook addition as `normal`.

## Related
- docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md
- docs/solutions/harness/gap-closure-decisions.md
