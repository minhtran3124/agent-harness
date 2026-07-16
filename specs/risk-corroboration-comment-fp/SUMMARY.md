# risk-corroboration-comment-fp — Summary

Lane: high-risk
Confidence: high
Reason: Edits hooks/risk-corroboration.sh — a hard-gate/high-blast path (Rule 4). Explicitly directed by the user ("tiếp tục C4"); the fix itself is prescribed verbatim by the repo's own knowledge doc.
Flags: high-blast (hooks/*)
Affects: hooks/risk-corroboration.sh (commit-time lane corroboration gate)
Input-type: harness improvement

### Intent

"merge PR #71 và tiếp tục C4" — per docs/reviews/over-engineering-review-2026-07-16.md §2 C4: the documented risk-corroboration false positive (auth words like "session"/"permission" in comments under tests/) is still unfixed; apply the repo's own failure memo.

## What changed

Full-line comments (`^\s*#` after the diff marker) are now stripped from `CODE_ADDED` and `CODE_REMOVED` before the keyword-category greps in `hooks/risk-corroboration.sh`. Chose the knowledge doc's **preferred** variant (comment-stripping) over the review's shorthand (`:!tests/` exclusion): excluding tests/ wholesale would blind the gate to a test that genuinely adds auth surface, while comment-stripping blind-spots only prose. Landed with the guardrail-required test cases (auth word in comment → no trip; same word in live code line under tests/ → still BLOCKED; removed comment → no weakening-validation trip). The knowledge doc's Guardrail line flipped `proposed:` → `applied (2026-07-16)`.

### Rationale

The scanner was reading natural-language prose as auth surface, and the previously applied "fix" was rewording comments to appease it (commit 0048a16) — backwards. Fixing the scanner's input set follows docs/solutions/harness/risk-corroboration-scans-test-comments-for-auth-words.md §Correct Approach, which explicitly prefers this variant and specifies the exact test contract this change ships.

### Alternatives considered

- `:!tests/` pathspec exclusion (review's one-liner): rejected per the knowledge doc — hides real auth code in tests from the gate.
- Rewording comments per-incident (status quo): rejected — behavior change to satisfy a scanner, unbounded recurrence.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| hook suite incl. 3 new guardrail cases | `bash tests/hooks/risk-corroboration.test.sh` | 0 | 15 passed |
| comment-strip present in both scan sets | `grep -c "grep -vE .^.\[\[:space:\]\]\*#." hooks/risk-corroboration.sh` | 0 | ADDED + REMOVED |
| FP doc guardrail flipped to applied | `grep -q "applied (2026-07-16)" docs/solutions/harness/risk-corroboration-scans-test-comments-for-auth-words.md` | 0 | memo consumed |
| gate-integration suite (cross-hook contract) | `bash tests/hooks/gate-integration.test.sh` | 0 | no regression |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |

### Rollback

- `git revert <commit>` — removes the two `grep -vE` filters and the new test cases; gate returns to prior (FP-prone) behavior. No data or config migration.

### Harness-Delta

- Recurring: stale-active `specs/correctness-review-angles/PLAN.md` warned on every edit again (third time this session) — flip it to shipped or teach finishing-a-development-branch to sweep stale-active plans.
