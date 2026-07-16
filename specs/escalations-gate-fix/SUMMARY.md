# escalations-gate-fix — Summary

Lane: high-risk
Confidence: high
Reason: Edits hooks/commit-quality-gate.sh — a hard-gate/high-blast path (Rule 4). Explicitly directed by the user ("tiếp tục C5"); enforce-vs-demote decision made in favor of enforcement (see Rationale).
Flags: high-blast (hooks/*)
Affects: hooks/commit-quality-gate.sh (commit gate), ESCALATIONS deny-on-no-response contract (rules/orchestration.md, templates/ESCALATIONS.template.md)
Input-type: harness improvement

### Intent

"merge PR #72 và #73, tiếp tục C5" — per docs/reviews/over-engineering-review-2026-07-16.md §2 C5: the ESCALATIONS "deny-on-no-response" gate is unenforced fiction (no hook/script reads ESCALATIONS.md; specs/resync-protected-files shipped with E001 `decision: pending`). Fix: a ~5-line check in commit-quality-gate.sh failing on `decision: pending`, or delete the claim.

## What changed

Chose **enforce** over demote: new Check 1.5 in `hooks/commit-quality-gate.sh` denies a commit (exit 2) when any staged path lies under `specs/<slug>/` whose `ESCALATIONS.md` contains `decision: pending`. Scoped to the touched slug only — a pending escalation elsewhere never freezes unrelated work — and the check reads the **staged** copy first, so the commit that records the decision self-unblocks. Doc claims updated to state the mechanization (rules/orchestration.md, templates/ESCALATIONS.template.md). Four new contract tests (suite 20 passed).

### Rationale

A deny gate that never denies corrupts the autonomy model — the escalation channel is what earns the "proceed without a human" default everywhere else. Enforcement cost ~20 lines in an existing commit gate; demoting the claim would have kept the channel but silently removed the only reason agents respect it. Slug-scoping was the key design choice: the recorded failure (resync-protected-files shipping over a pending E001) is precisely "work on the escalated slug proceeded", so that is exactly what blocks — nothing broader.

### Alternatives considered

- Demote to "decision log" (review's alternative): rejected — keeps the artifact, deletes its meaning.
- Repo-wide block while any escalation is pending: rejected — the standing pending E001 would freeze all commits; punishes unrelated work.
- Enforce in ci-strict-gate instead of the commit hook: rejected — CI-only enforcement fires after the work is pushed; the commit hook stops it at write time, and CI still sees the result via the tests.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| hook suite incl. 4 new escalation cases | `bash tests/hooks/commit-quality-gate.test.sh` | 0 | 20 passed |
| check reads staged copy first (self-unblock) | `grep -q "git show .:.esc." hooks/commit-quality-gate.sh` | 0 | staged wins |
| pending pattern anchored to decision lines | `grep -q "decision:\[\[:space:\]\]\*pending" hooks/commit-quality-gate.sh` | 0 | not a free-text match |
| orchestration rule states the mechanization | `grep -q "Mechanized by .hooks/commit-quality-gate.sh." rules/orchestration.md` | 0 | claim now true |
| template states the enforcement | `grep -q "Enforced: .hooks/commit-quality-gate.sh." templates/ESCALATIONS.template.md` | 0 | |
| gate-integration suite | `bash tests/hooks/gate-integration.test.sh` | 0 | cross-hook contract intact |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |

### Rollback

- `git revert <commit>` — removes Check 1.5, the tests, and the two doc lines; the deny claim returns to unenforced (prior behavior). No data/config migration.

### Harness-Delta

- The standing `specs/resync-protected-files/ESCALATIONS.md` E001 remains `decision: pending` — deliberately NOT resolved here (human decision by contract). With this gate live, any commit touching that slug blocks until the user records a decision; option A already matches shipped reality, so recording it is a one-line human edit.
