# SUMMARY — correctness-review-upgrade

**Lane:** normal
**Confidence:** high
**Reason:** Prose edits to two skill-prompt docs in `skills/subagent-driven-development/`. Reversible (`git revert`), no app code, no hard gate. Verified by grep assertions + two fresh-context reviews.

## Rationale

External AI reviewers (added by the client) catch real runtime bugs our design/plan/review chain misses, because our per-task reviews are anchored to the plan as the oracle — a bug that faithfully implements a flawed spec passes them. We grafted three mechanics from Every's `/ce-code-review` onto the final adversarial correctness review:

- **C — compound read-back:** reviewer reads `docs/solutions/critical-patterns.md` + `failure` track (graceful when absent), turning past bugs into checks. Closes the compound loop at review time — previously only `/xia2` and `/brainstorming` pulled from `docs/solutions/`.
- **D — two-axis classification:** every finding gets `Severity P0–P3` × `Rule 1–4` (reuses `.claude/rules/auto-correct-scope.md`, no new taxonomy).
- **E — residual work gate:** unresolved findings must land in `SUMMARY.md` (Rule 1–3) or `ESCALATIONS.md` (Rule 4); nothing silently dropped.

## Alternatives considered

- **Boris `/code-review` find→score→threshold + multi-lens fan-out** — deferred (out of scope here); the precision-filter pattern is the next candidate.
- **B — feature-intake flag→reviewer-persona mapping** — deferred as a separate high-blast follow-up (touches `skills/feature-intake/`).
- **SessionStart hook to auto-load critical-patterns** (the "medium" loop-closure option from `docs/research-compound-loop-closure.md`) — deferred; Rule 4 high-blast (`settings.json` + hook).

## Deviations

- (review fix, not auto-applied beyond spec) Reworded `## Fix loop` item 4 in `correctness-reviewer-prompt.md` to remove a contradiction the new Rule-class taxonomy exposed ("Each fix is a Rule 1 auto-fix" → Rule 1–3 logged / Rule 4 escalates). Flagged by spec/consistency review.
- (controller) Changed `SKILL.md` P3 label "style / minor" → "minor correctness issue" — the reviewer's Out-of-scope explicitly excludes style.

### Verify

| Check | Command | Exit | Notes |
|---|---|---|---|
| Task 1 (C) | `grep critical-patterns.md + compound read-back + failure + graceful-skip` | 0 | prompt file |
| Task 2 (D) | `grep P0 + P3 + Rule 4 + auto-correct-scope.md` | 0 | prompt file |
| Task 3 (E) | `grep residual work gate + ESCALATIONS.md + SUMMARY.md` | 0 | prompt file |
| Task 4 (wire) | `grep compound read-back + Rule 4 + residual + ESCALATIONS` | 0 | SKILL.md |
| Task 5 (lint) | `grep correctness-reviewer-prompt.md + test -f rules` | 0 | cross-file |
| No contradiction | `grep -c "Each fix is a Rule 1 auto-fix" == 0` | 0 | prompt file |
| No leftover single-axis severity | `grep -E "Critical \(|High \(|Medium \("` → none | 0 | prompt file |

### Rollback

- Revert both files: `git checkout main -- skills/subagent-driven-development/SKILL.md && rm skills/subagent-driven-development/correctness-reviewer-prompt.md`
- Or, if committed: `git revert <sha>`

### Review Findings

None unresolved. Two findings (Fix-loop contradiction, xia2 citation off-by-one) were raised by review and fixed in-loop; see Deviations.
