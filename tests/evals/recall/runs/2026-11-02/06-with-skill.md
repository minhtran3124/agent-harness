Verdict: reusable pattern

**Do first**
- Trim by whole sentences or whole blocks, never by cutting words inside a sentence. Run the deletion test on each sentence: delete it if the model already does it by default. A sentence that restates something the skill already makes the model read passes the test, but a bare pointer does not. Move blocks that only some branches reach into `references/` and leave a one-line pointer. `docs/solutions/harness/deletion-test-for-word-ceiling.md` (confirmed_at 2026-10-16). Command: `python3 scripts/audit_skill_prompts.py`. It shows each skill's word count.
- Keep any sentence that holds a condition word whole, or move it whole. The words are if, unless, only, when, never, except, for a new, and without. When a moved or deleted sentence sits under a leading condition, move the condition with the block or repeat it beside the sentences that stay. `docs/solutions/harness/deletion-test-for-word-ceiling.md` (2026-10-16); `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md` (2026-10-15).
- Before you delete a sentence, grep it against `tests/` and `hooks/`, because a shell test may pin it. Name new `references/` files without "prompt", because the audit counts `skills/**/*prompt*.md` as companion prompts. If the skill is still over budget when nothing safe is left, stop. List the remaining sentences as "kept long on purpose" in the spec's `SUMMARY.md`. `docs/solutions/harness/deletion-test-for-word-ceiling.md` (2026-10-16).

**Avoid**
- Do not split a sentence of the form "X if present: A; B; C" without repeating the scope on each part. Only the first part keeps the condition. Steps then run unconditionally, for example intake stopping on every legacy slug.
- Do not cut a condition word to reach 600 words, for example "For a new SUMMARY, write it from" becoming "Write a new SUMMARY from". The step then reads as an order to overwrite the existing SUMMARY.
- Do not treat a green test suite or a lower STE lint count as proof that the meaning is unchanged. Both were green on the two broken rewrites.

**Check before done**
- Give each trimmed file a line-by-line meaning-equivalence review that compares every removed line with its replacement and looks for dropped conditions, exceptions and scope qualifiers. The brief must ask for it, because the task reviewer does not run it on its own.
- Resolve each condition word the scope-qualifier check lists as "kept" with a cited HEAD line, or restore it. This is the `check_scope_qualifiers.py` step from the deletion-test record. Because that script is missing (see Possibly stale), do this by hand-diffing the removed and added lines for the eight condition words.
- "Kept long on purpose" covers the word budget only. It never closes a lost condition.

**Already decided**
- `docs/solutions/harness/ste100-adoption-decisions.md` (2026-10-15): the STE linter is a warn-only ratchet and not a blocking gate, `synonym-rotation` is excluded from the counts, and a vendored skill that has `UPSTREAM.md` is exempt from the 600-word ceiling. Any bulk prose rewrite needs a per-file meaning-equivalence review.

**Possibly stale**
- `scripts/check_scope_qualifiers.py` does not exist in the repo. I also found no copy under `plugins/harness/`. The `--base/--head` command in the deletion-test record and the proposed Guardrail in the scope-qualifiers record cannot run. The principle still holds.
- The `## Scope qualifiers` section of the review package cannot be confirmed. `skills/subagent-driven-development/scripts/review_package.py` is missing, and I found no copy under `plugins/harness/`.
- The affects paths `skills/feature-intake/SKILL.md`, `skills/subagent-driven-development/SKILL.md`, `rules/orchestration.md` and `skills/*/SKILL.md` are missing at the repo root. Under `plugins/harness/` there is no `feature-intake`, no `subagent-driven-development` and no `rules/orchestration.md`. Skills now live at `plugins/harness/skills/<name>/SKILL.md`, and `intake` is probably the successor of `feature-intake`. The principles still hold.
- `skills/asd-ste100/UPSTREAM.md` moved to `plugins/harness/skills/asd-ste100/UPSTREAM.md`.
- `scripts/audit_skill_prompts.py` still exists, and its ceiling is `SKILL_WORD_CEILING = 600`. `scripts/check_ste_baseline.py` and `scripts/ste-baseline.json` also exist.
- All three records are about 19 to 20 days old (today is 2026-11-04), which is under 30 days. No record is over 30 days old.

**Search surface:** `/home/minhtran/Documents/minh.tran/projects/.ship-agent-harness/recall-brief/t556/docs/solutions/INDEX.md`, `/home/minhtran/Documents/minh.tran/projects/.ship-agent-harness/recall-brief/t556/docs/solutions/critical-patterns.md`, `/home/minhtran/Documents/minh.tran/projects/.ship-agent-harness/recall-brief/t556/docs/solutions/harness/deletion-test-for-word-ceiling.md`, `/home/minhtran/Documents/minh.tran/projects/.ship-agent-harness/recall-brief/t556/docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`, `/home/minhtran/Documents/minh.tran/projects/.ship-agent-harness/recall-brief/t556/docs/solutions/harness/ste100-adoption-decisions.md`. I checked the affects paths with ls and find under the repo root and `plugins/harness/`.
