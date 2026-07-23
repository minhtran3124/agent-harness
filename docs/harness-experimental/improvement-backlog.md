# Improvement Backlog

Proposed mechanical guardrails mined from `/compound` failure tracks. Each row is a ratchet
candidate: a hook/test/lint/rule to build so a known mistake cannot recur. Triage and check off.

This closes the loop from "documented learning" → "mechanically enforced rule" (OpenAI's ratchet
principle): a `failure` track whose `Guardrail` is tagged `proposed:` lands here automatically.

| Date | From failure (slug) | Proposed guardrail | Target path | Status |
|---|---|---|---|---|
| 2026-06-14 | pretooluse-hook-denies-combined-git-add-commit | Refine the untracked-`.py` check to also pass when the call's own `git add` targets (or the staged set) would cover the untracked files; or document a "stage and commit in separate Bash calls" rule | `hooks/check-untracked-py.sh` | done (2026-07-04, docs-only route — see CLAUDE.md Gotchas) |
| 2026-07-10 | risk-corroboration-scans-test-comments-for-auth-words | Strip `^\s*#` comment lines from CODE_ADDED/CODE_REMOVED before the category greps (preferred), or add `':!tests/'` to the pathspecs at lines 71 and 74; land with a tests/hooks/ case proving an auth word in a comment does not trip the gate while one in live code still does | hooks/risk-corroboration.sh | open |
| 2026-07-17 | verify-row-must-be-pipe-free-and-under-60s | lint SUMMARY Verify command cells: fail on a pipe in the command or a full-suite/build invocation | scripts/check_verify_rows.py | done (#TBD) |
| 2026-07-21 | manual-version-bump-collides-with-event-sourced-bookkeeping | CI check that fails a non-bookkeeping PR whose diff touches `VERSION` or the `## [Unreleased]` CHANGELOG section (the finishing-skill Step-1b removal is the doc fix; this is the mechanical backstop) | .github/workflows/harness-ci.yml (or a new check) | open |
| 2026-07-23 | stale-active-plan-misaims-blast-radius | "merged-but-active" check: fail/warn when a specs/*/PLAN.md has `status: active` but its spec branch is merged into main | scripts/lint-doc-truth.sh (or new scripts/check_plan_status.py wired into run-tests.sh L1) | open |
| 2026-07-23 | gate-config-must-read-index | index-vs-worktree angle in correctness review: for any diff touching a PreToolUse commit hook, enumerate every file the hook reads and require each tagged index-side (`git show :`) or justified worktree-side (commit-quality-gate.sh Check 1.6 worktree fallback is a known live instance) | skills/correctness-review/SKILL.md | open |
