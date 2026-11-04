Verdict: existing decision

**Do first**
- Run the pilot-then-gate sequence before any bulk STE rewrite: rewrite about three files, measure with comprehension probes and real runs, then gate the rollout. `docs/solutions/harness/ste100-adoption-decisions.md` (confirmed_at 2026-10-15), Decision 1.
- Ask the task reviewer for a per-file meaning-equivalence review in every rewrite brief. The reviewer prompt does not run one on its own. Repeat the scope on each part when you split "X if present: A; B; C". Never cut a condition word to meet the ceiling. `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md` (confirmed_at 2026-10-15).
- To vendor a skill, copy it into `skills/asd-ste100/` with an `UPSTREAM.md` that lists the deltas. Do not commit the `npx skills` install. `docs/solutions/harness/ste100-adoption-decisions.md` (2026-10-15), Decision 2.

**Avoid**
- Do not use the STE lint count as proof for `*-prompt.md` dispatch prompts. `ste-lint.py` skips fenced blocks, so the count shows `0 → 0` over the most important prose. This happened twice. `ste-rewrite-drops-scope-qualifiers.md` and `ste-ratchet-blind-to-fenced-prompt-prose.md`.
- Do not cut condition words ("For a new…", "if present") to reach the 600-word ceiling. On a legacy slug, intake would stop or overwrite the existing SUMMARY. The tests and the lint count stay green.
- Do not treat a lint rise on eval fixtures as Important. Fixtures are out of STE scope, so record the rise as a plan-mandated Minor finding.

**Check before done**
- Record in `### Not auto-verified` that the lint count does not cover fenced prompt prose. Then check each fenced hunk by hand.
- Check that the two `DISABLED_RULES` constants are equal (`check_ste_baseline.py` and the review package) and still exclude `synonym-rotation`.
- Check that the ratchet still exits 0 by default. `--strict` exits 1 on a WARN and on a skipped run.

**Already decided**
- Rollout gate (Decision 1): pilot then gate. The pilot rewrote three files, ran 80 trials and passed all of them. Phase 3 is a separate plan.
- Vendoring (Decision 2): vendor into `skills/asd-ste100/` from upstream `3944283c18`. Updates are a manual re-vendor. `audit_skill_prompts.py` exempts any skill directory that has `UPSTREAM.md` from the 600-word ceiling.
- Ratchet scope (Decision 3): `synonym-rotation` is excluded from the baseline and the review-package counts, because the earlier research measured no effect. Do not turn an unmeasured rule into a blocking gate.
- Ratchet mode (Decision 4): the ratchet is warn-only in `run-tests.sh`, and `--strict` is used only by plan checks. There is no blocking CI or hook gate. `--against <git-ref>` compares each file with its baseline entry at that ref.

**Possibly stale**
- All three records are 20 days old (confirmed_at 2026-10-15 and 2026-10-16), so none is over 30 days. The principles above still hold.
- `skills/subagent-driven-development/scripts/review_package.py` is not found. Glob found no `review_package.py` in the repo. The `DISABLED_RULES` and `## STE lint` advice that depends on it is unverified until you locate the file or its replacement under `plugins/harness/`.
- `skills/subagent-driven-development/task-reviewer-prompt.md` and `skills/subagent-driven-development/SKILL.md` are not found at those paths. Glob found no `task-reviewer-prompt.md`. The "add a meaning-equivalence instruction to the task-reviewer prompt" guardrail is only proposed, so it is unverified.
- `skills/subagent-driven-development/implementer-prompt.md` has moved to `plugins/harness/skills/implement/implementer-prompt.md`.
- `skills/asd-ste100/*` and `skills/feature-intake/SKILL.md` have moved under `plugins/harness/skills/`. I confirmed this for `UPSTREAM.md` and `scripts/ste-lint.py`. I did not check `feature-intake`.
- `specs/ste100-prose-rollout/PLAN.md` is not found. The spec is not in the repo.
- `scripts/check_ste_baseline.py`, `scripts/ste-baseline.json` and `scripts/audit_skill_prompts.py` exist. `DISABLED_RULES`, `--strict` and `--against` appear in `check_ste_baseline.py`, and `UPSTREAM` appears in `audit_skill_prompts.py`. I did not read their code.
- `rules/orchestration.md` is not checked.
- The proposed guardrails (a fence-aware lint and `check_scope_qualifiers.py`) are only proposed. I did not find `check_scope_qualifiers.py`.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/ste100-adoption-decisions.md`, `docs/solutions/harness/ste-ratchet-blind-to-fenced-prompt-prose.md`, `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`. Path checks by Glob and Grep over the repo root and `scripts/`.
