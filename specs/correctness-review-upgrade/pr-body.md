## Summary

Two related-but-distinct changes to the skill framework, one commit each.

### 1. `feat(review)` — adversarial correctness review stage (`41bb667`)

Adds a **final whole-diff adversarial correctness review** to `subagent-driven-development`, then upgrades it with three mechanics borrowed from Every's `/ce-code-review` (compared against Boris's `/code-review` during design):

- **C — compound read-back:** the reviewer reads `docs/solutions/critical-patterns.md` + the `failure` track (graceful when absent), turning each past bug into a check. **Closes the compound loop at review time** — previously only `/xia2` and `/brainstorming` pulled from `docs/solutions/` (see `docs/research-compound-loop-closure.md`).
- **D — two-axis classification:** every finding carries `Severity P0–P3` × `Rule 1–4` (reuses `.claude/rules/auto-correct-scope.md`, no new taxonomy).
- **E — residual work gate:** unresolved findings must land in `SUMMARY.md` (Rule 1–3) or `ESCALATIONS.md` (Rule 4); nothing silently dropped.

**Why:** per-task spec/quality reviews are anchored to the plan as the oracle, so a bug that *faithfully implements a flawed spec* passes them — the gap that let real bugs reach production and get caught by external (client-added) AI reviewers post-push.

Files: `skills/subagent-driven-development/SKILL.md`, `skills/subagent-driven-development/correctness-reviewer-prompt.md` (new).

### 2. `chore` — remove `incremental-implementation` skill (`768acab`)

Not in the active workflow. Deletes `skills/incremental-implementation/` and scrubs references from `CLAUDE.md`, `README.md`, `skills/README.md`. Active execution paths remain `subagent-driven-development` (same session) and `executing-plans` (parallel).

## Verification

Markdown skill-doc change only (0 `.py` on branch; repo has no `apps/api` suite). Verified via grep assertions (Tasks 1–5, all exit 0) + two fresh-context reviews (which caught and fixed a Fix-loop contradiction and an off-by-one citation).

## Follow-ups (deferred, not in this PR)

- **B** — `feature-intake` flag → reviewer-persona mapping (separate high-blast change).
- Boris-style find→score→threshold + multi-lens fan-out.
- After re-sync, ensure the deployed `.claude/skills/` copy picks up these source edits.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
