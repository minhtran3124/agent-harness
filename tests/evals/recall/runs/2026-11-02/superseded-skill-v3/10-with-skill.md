Verdict: existing decision

**Do first**
- Treat `docs/solutions/harness/ste100-adoption-decisions.md` (confirmed_at 2026-10-15) as the baseline. Keep the ratchet warn-only. `python3 scripts/check_ste_baseline.py` always exits 0, and only plan checks use `--strict`. Vendor a third-party skill into `plugins/harness/skills/<name>/` with an `UPSTREAM.md` that lists the deltas. Do not use an `npx skills add` install.
- Before any bulk rewrite, run a pilot of about three files. Measure comprehension and real runs, and gate the rollout on the result. For each rewritten file, brief the task reviewer to compare each removed line with its replacement. Source: `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md` (confirmed_at 2026-10-15). When you split "X if present: A; B; C", repeat the scope on each part. Never cut a condition word to fit the 600-word ceiling.
- Rewrite fenced dispatch-prompt prose in `*-prompt.md` files in Strict mode, and check each fenced hunk by hand. Source: `docs/solutions/harness/ste-ratchet-blind-to-fenced-prompt-prose.md` (confirmed_at 2026-10-16).

**Avoid**
- Do not use the STE lint count as proof that a rewrite is done. A rewrite dropped two conditions in `feature-intake`, and the lint count went down while the agent behavior changed.
- Do not trust the `0 → 0` lint result for fenced dispatch prompts. `ste-lint.py` skips fenced blocks, so about 25 new prompt lines showed no change. Record this in `### Not auto-verified`.
- Do not add a blocking gate on a lint rule with no measured effect. `synonym-rotation` measured null, so it is in `DISABLED_RULES`.

**Check before done**
- Run `grep -n DISABLED_RULES scripts/check_ste_baseline.py` and confirm any second constant in the review package equals `("synonym-rotation",)`. The decision record says to keep the two equal.
- If you change a vendored skill, check that `UPSTREAM.md` exists. `scripts/audit_skill_prompts.py` only exempts a skill from the 600-word ceiling when that file is present. Any skill can add the marker, so this exemption is self-declared.
- For each rewritten file, check that every removed condition word (if, unless, only, when, never, except, "for a new") appears in the replacement.

**Already decided**
- `docs/solutions/harness/ste100-adoption-decisions.md`: pilot then gate; vendor into `skills/asd-ste100/` and exempt it from the word ceiling by `UPSTREAM.md`; exclude `synonym-rotation` from the review-package count and the baseline; the ratchet is warn-only, `--strict` exits 1 on a skipped run, and `--against <git-ref>` compares against a baseline at that ref.

**Possibly stale**
- `docs/solutions/harness/ste100-adoption-decisions.md`: the `affects` paths `skills/asd-ste100/UPSTREAM.md` and `skills/subagent-driven-development/scripts/review_package.py` are not at those locations. `UPSTREAM.md` now lives at `plugins/harness/skills/asd-ste100/UPSTREAM.md`. I found no `review_package.py` under `plugins/`, so the review-package half of Decision 3 may no longer apply. The advice still holds for `check_ste_baseline.py` and `audit_skill_prompts.py`, which exist. The record is 20 days old.
- `docs/solutions/harness/ste-ratchet-blind-to-fenced-prompt-prose.md`: `specs/ste100-prose-rollout/PLAN.md` and `skills/subagent-driven-development/task-reviewer-prompt.md` do not exist. `implementer-prompt.md` moved to `plugins/harness/skills/implement/`. The core advice holds because `plugins/harness/skills/asd-ste100/scripts/ste-lint.py` and `scripts/check_ste_baseline.py` exist. Its proposed guardrails (a `--include-fences` mode, a shared prose-path definition) are still unbuilt. The record is 19 days old.
- `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`: `skills/feature-intake/SKILL.md` and `rules/orchestration.md` are not at those paths, and `skills/subagent-driven-development/SKILL.md` was not checked. The advice still holds. I found no `scripts/check_scope_qualifiers.py`, so that guardrail is still unbuilt. The record is 20 days old.

Search surface: docs/solutions/INDEX.md, docs/solutions/critical-patterns.md, docs/solutions/harness/ste100-adoption-decisions.md, docs/solutions/harness/ste-ratchet-blind-to-fenced-prompt-prose.md, docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md
