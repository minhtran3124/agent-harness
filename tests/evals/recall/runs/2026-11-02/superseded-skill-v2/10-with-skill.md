Verdict: existing decision (STE adoption is settled; the ratchet is warn-only and the pilot gated the rollout), with two known risks.

**Do first**
- Read `docs/solutions/harness/ste100-adoption-decisions.md` (confirmed_at 2026-10-15) before you touch any STE check or vendor a skill. It says to run a pilot, then gate the rollout on the result. It says to vendor into `skills/asd-ste100/` and record the deltas in `UPSTREAM.md`. It says to keep the ratchet warn-only.
- For a new lint rule, check `DISABLED_RULES` in `scripts/check_ste_baseline.py`. The decision says to exclude a rule with no measured effect, such as `synonym-rotation`, from the counts. The decision also says to keep the two `DISABLED_RULES` constants equal. The second constant is in `review_package.py`, which I could not find (see Possibly stale).
- Use the `--strict` and `--against <git-ref>` modes of the ratchet when a plan check needs it. Command: `python3 scripts/check_ste_baseline.py [--strict | --update] [--against REF]`. The default run always exits 0. `--strict` exits 1 on a WARN or a skipped run.

**Avoid**
- Do not use the STE lint count as proof that a rewrite is done for `*-prompt.md` dispatch prompts (`docs/solutions/harness/ste-ratchet-blind-to-fenced-prompt-prose.md`, confirmed_at 2026-10-16). `ste-lint.py` skips fenced blocks, so the count showed `0 → 0` for about 25 new fenced prompt lines (twice).
- Do not split sentences or cut words to fit the 600-word ceiling without a meaning check (`docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`, confirmed_at 2026-10-15). Two scope conditions were dropped ("if present", "For a new SUMMARY"). All tests passed and the lint count went down.
- Do not block a build or commit on a rule with no measured effect. The earlier measurement found only machine-decidable acceptance criteria had an effect (`docs/solutions/harness/ste100-adoption-decisions.md`).

**Check before done**
- The task brief asks the task reviewer for a per-file meaning-equivalence review. The task-reviewer prompt does not run one on its own.
- `### Not auto-verified` records that the lint count does not cover fenced prompt prose. Every fenced hunk is reviewed by hand.
- No condition word was cut to meet the ceiling. For a vendored skill, `UPSTREAM.md` exists, because `audit_skill_prompts.py` exempts a skill directory that has that file.

**Already decided**
- `docs/solutions/harness/ste100-adoption-decisions.md`: pilot three files then gate the rollout; vendor into `skills/asd-ste100/` with `UPSTREAM.md` deltas and an exemption from the word ceiling; exclude `synonym-rotation` from the counts; the ratchet is warn-only, and `--strict` exits 1 on a skipped run.

**Possibly stale**
- `docs/solutions/harness/ste100-adoption-decisions.md`: all its `affects` paths are older than 30 days (about 18 days old, so not yet). `skills/asd-ste100/UPSTREAM.md` is now at `plugins/harness/skills/asd-ste100/UPSTREAM.md`. The `affects` path `skills/subagent-driven-development/scripts/review_package.py` is not found in the repo, so the second `DISABLED_RULES` constant and the review-package `## STE lint` section may be gone.
- `docs/solutions/harness/ste-ratchet-blind-to-fenced-prompt-prose.md`: `specs/ste100-prose-rollout/PLAN.md` and `skills/subagent-driven-development/task-reviewer-prompt.md` are missing. The skill `subagent-driven-development` no longer exists under `plugins/harness/skills/`. `implementer-prompt.md` has moved to `plugins/harness/skills/implement/`. The fence blind spot in `ste-lint.py` may still apply, because that file still exists. I did not read it.
- `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`: `skills/feature-intake/SKILL.md` is now `plugins/harness/skills/intake/SKILL.md`. `skills/subagent-driven-development/SKILL.md` and `rules/orchestration.md` are missing. The lesson holds, but the examples point at old paths.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/ste100-adoption-decisions.md`, `docs/solutions/harness/ste-ratchet-blind-to-fenced-prompt-prose.md`, `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`; Glob and Grep over `scripts/` and `plugins/harness/skills/` for the `affects` paths.
