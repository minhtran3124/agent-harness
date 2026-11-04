Verdict: reusable pattern

**Do first**
- Trim by whole sentences, not by cutting words inside a sentence. For each sentence, apply the deletion test: if the model already does it by default, delete the whole sentence. Move a whole block that only some branches reach into `references/`, and leave a one-line pointer. Do not name the new file with `prompt`, because the audit counts those as companion prompts. docs/solutions/harness/deletion-test-for-word-ceiling.md (confirmed_at 2026-10-16). Command: `python3 scripts/audit_skill_prompts.py`.
- Never shorten a sentence that holds a condition word (`if`, `unless`, `only`, `when`, `never`, `except`, `for a new`, `without`). Keep it whole or move it whole. If a moved sentence sat under a leading condition, repeat that condition beside every sentence that depends on it. docs/solutions/harness/deletion-test-for-word-ceiling.md and docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md (confirmed_at 2026-10-15).
- If the skill is still over 600 words and nothing safe is left, stop. List the remaining sentences as "kept long on purpose" in the spec's `SUMMARY.md`. This covers the word budget only and never excuses a lost condition. docs/solutions/harness/deletion-test-for-word-ceiling.md (confirmed_at 2026-10-16).

**Avoid**
- Cutting a few words to reach the ceiling. In feature-intake, "For a new SUMMARY, write it from" became "Write a new SUMMARY from". A legacy slug then read as an order to overwrite its existing SUMMARY, and every test still passed.
- Splitting "X if present: A; B; C" into short sentences. Only the first sentence keeps the condition. Intake would then stop on every legacy slug with no intent.md, and "ask the user to commit" would run unconditionally.
- Treating a green test suite or a lower STE lint count as proof that the meaning is unchanged. Tests match literal strings and do not check which steps are conditional.

**Check before done**
- Have a reviewer compare each removed line with its replacement, line by line, for dropped conditions, exceptions and scope qualifiers. The task reviewer prompt does not do this on its own, so ask for it in the task brief.
- Before you delete a sentence, grep it against `tests/` and `hooks/`, because a shell test may pin it.
- Run `python3 scripts/audit_skill_prompts.py` and confirm the SKILL.md is at or under 600 words with room for the new sentences.

**Already decided**
- docs/solutions/harness/ste100-adoption-decisions.md: a vendored skill with an `UPSTREAM.md` is exempt from the 600-word ceiling, and the STE ratchet is warn-only.

**Possibly stale**
- docs/solutions/harness/deletion-test-for-word-ceiling.md (19 days old): `scripts/check_scope_qualifiers.py` does not exist in the repo, so the review step that uses it is unavailable. `scripts/audit_skill_prompts.py` exists. The pattern still holds, so do the condition-word check by hand.
- docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md (20 days old): the `affects` paths `skills/feature-intake/SKILL.md`, `skills/subagent-driven-development/SKILL.md` and `rules/orchestration.md` are not at the repo root. A search found no `feature-intake` or `subagent-driven-development` under `plugins/harness/skills/`, which has an `intake` skill. The advice still holds. Its Guardrail section is only "proposed", and the script it names is missing.
- docs/solutions/harness/ste100-adoption-decisions.md (20 days old): its `affects` path `skills/asd-ste100/UPSTREAM.md` is now at `plugins/harness/skills/asd-ste100/UPSTREAM.md`, and `skills/subagent-driven-development/scripts/review_package.py` was not found. `scripts/check_ste_baseline.py`, `scripts/ste-baseline.json` and `scripts/audit_skill_prompts.py` exist.

**Search surface:** docs/solutions/INDEX.md, docs/solutions/critical-patterns.md, docs/solutions/harness/deletion-test-for-word-ceiling.md, docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md, docs/solutions/harness/ste100-adoption-decisions.md
