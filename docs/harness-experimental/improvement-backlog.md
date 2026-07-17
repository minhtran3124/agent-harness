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
