Verdict: reusable pattern

**Do first**
1. Trim whole sentences, not words inside a sentence. For each sentence, apply the deletion test: if the model already does it by default, delete the whole sentence. Move a block that only some branches reach into `references/` and leave a one-line pointer. Do not name the new file with `prompt`, because the audit counts those as companion prompts. Source: `docs/solutions/harness/deletion-test-for-word-ceiling.md`, confirmed_at 2026-10-16. Command: `python3 scripts/audit_skill_prompts.py`.
2. Never shorten a sentence that holds a condition word (`if`, `unless`, `only`, `when`, `never`, `except`, `for a new`, `without`). Keep it whole or move it whole. If a moved or deleted sentence sat under a leading condition, repeat that condition beside every sentence that depends on it. Source: `docs/solutions/harness/deletion-test-for-word-ceiling.md`, confirmed_at 2026-10-16.
3. If the SKILL.md is still over budget after the safe cuts, stop. Keep the remaining sentences and list them as "kept long on purpose" in the spec's `SUMMARY.md`. Source: `docs/solutions/harness/deletion-test-for-word-ceiling.md`, confirmed_at 2026-10-16.

**Avoid**
- Do not cut words to meet the ceiling. In `feature-intake`, cutting "For a new SUMMARY, write it from" to "Write a new SUMMARY from" removed a condition, and the step then read as an order to overwrite an existing SUMMARY. All tests passed and the lint count went down (`docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`).
- Do not split a sentence such as "X if present: A; B; C" without repeating the scope. Only the first part keeps the condition. In the pilot, intake would have stopped on every legacy slug that had no `intent.md` (same record).

**Check before done**
- Review each trimmed file line by line, comparing every removed line with its replacement for dropped conditions, exceptions and scope qualifiers. The task-reviewer prompt does not run this check on its own, so you must ask for it.
- Before you delete a sentence, grep it against `tests/` and `hooks/`, because a shell test may pin it.
- Treat green tests and a lower STE lint count as no evidence of equal meaning. A "kept long on purpose" note never closes a lost condition.

**Already decided**
- `docs/solutions/harness/ste100-adoption-decisions.md`: the STE lint is a warn-only ratchet (not a blocking gate), vendored skills with `UPSTREAM.md` are exempt from the 600-word ceiling, and `synonym-rotation` is excluded from the counts.

**Possibly stale**
- `docs/solutions/harness/deletion-test-for-word-ceiling.md`: it says to run `scripts/check_scope_qualifiers.py`, and that file does not exist anywhere in this worktree. `scripts/audit_skill_prompts.py` does exist. The record's STE-lint and scope-check advice is unverified, so do not rely on that script.
- `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`: its Guardrail section marks `check_scope_qualifiers.py` as "proposed", which fits the script's absence. The `affects` paths `skills/...` and `rules/...` are at repo root, not under `plugins/harness/`. Skills live at `plugins/harness/skills/<name>/SKILL.md` here, and `skills/feature-intake` was not found under that path, so this path premise may be outdated.
- All three records are about 17 days old (confirmed 2026-10-15 and 2026-10-16, today 2026-11-02), so none is past 30 days.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/deletion-test-for-word-ceiling.md`, `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`, `docs/solutions/harness/ste100-adoption-decisions.md`. Also searched by glob and grep: `scripts/audit_skill_prompts.py` (exists), `check_scope_qualifiers.py` (not found), `plugins/harness/skills/*/SKILL.md`.
