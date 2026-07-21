# dynamic-rule-loading — Summary

Lane: normal
Confidence: high
Reason: flags 8 (changes existing always-on rule-loading behavior) and 9 (no automated proof around rule-loading semantics — needs Phase-0 empirical test); no hard gates — no settings.json/hooks/skill-engine changes.
Flags: existing behavior, weak proof
Affects: rules/ (plan-format, wave-parallelism, auto-correct-scope), skills/ (writing-plans, executing-plans, subagent-driven-development), CLAUDE.md + skills/README.md wording
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> "tôi đang suy nghĩ về việc load dynamic rule, hien tại tất cả các rules đều dc load khi claude chay. hãy suy nghi ve việc load on demand, vd nhu khi generate ra plan thi moi load rule plan-format, khi nao execution lien quan den wave thi moi load wave-parallelism, etc ... Make deep research ve van de nay"

then, after the research doc (`docs/research/2026-07-21-dynamic-rule-loading-research.md`) was delivered with a per-rule recommendation and phasing:

> "Ok, chay di"

Scope note recorded at intake: this task implements Phase 0 (verify `paths:` semantics), Phase 1 (`paths:` on plan-format + wave-parallelism, Step-0 Read lines in consuming skills), Phase 2 (auto-correct-scope scoping) and the doc wording updates. **Phase 3 (orchestration.md core split) is deferred** to its own change per the research doc §5.5 (needs a blind-run eval; most-referenced rule).

## What changed

Two-tier rule loading: `plan-format.md`, `wave-parallelism.md` (`paths: specs/**/PLAN.md`) and
`auto-correct-scope.md` (`paths: specs/**`) now carry `paths:` frontmatter so they load on
demand instead of every session (~15 KB off the always-on payload once deployed); the three
consuming skills (`writing-plans`, `executing-plans`, `subagent-driven-development`) gained
explicit Read steps because Phase-0 testing (v2.1.216) showed `paths:` injects on Read of a
matching file but NOT on Write of a new one — the skill Read is load-bearing for authoring
flows. CLAUDE.md documents the two-tier model. **Deployment pending:** `.claude/rules/` copies
in this repo are not synced (deploy requires explicit human confirmation per standing memory);
until deploy/install runs, runtime behavior is unchanged.

### Rationale

Implements the research doc's recommendation: deterministic load triggers only — official `paths:` frontmatter (belt) + explicit skill Step-0 Read lines (braces) — because prior art (Cursor Agent-Requested failures) shows model-judgment triggers silently miss, while always-on context measurably degrades instruction-following (context rot).

### Alternatives considered

- Hook-injected context (`additionalContext`) — rejected as default: touches high-blast `settings.json`/`hooks/` surface; reserved for must-not-miss rules.
- Repackaging rules as skills — rejected: moves trigger into the unreliable model-judgment class and breaks the rules-vs-skills split.
- Doing Phase 3 (orchestration split) in the same change — deferred: research doc flags it as the only risky edit, needing its own eval.

### Deviations

- Rule 1 — Fixed stale comment "rules/*.md auto-load every session" in `scripts/lint-doc-truth.sh` (reviewer finding 4; the change made it false). Added to PLAN Task 2.1 Files after blast-radius warning.
- Route deviation — in-place branch `feat/dynamic-rule-loading` instead of a worktree: per recorded memory, no-deploy worktrees break the Skill tool in this repo.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Phase-0 T1: scoped rule absent at session start | `claude -p --model haiku` in scratchpad mini-project | 0 | answered CODEWORD-ALWAYS only |
| Phase-0 T2: scoped rule injects on Read of matching file | `claude -p --model haiku` with Read specs/demo/PLAN.md | 0 | answered both codewords |
| Phase-0 T3: no injection on Write of new matching file | `claude -p --model haiku --permission-mode acceptEdits` | 0 | ALWAYS only → skill Read step is load-bearing |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | after frontmatter added |
| Read lines present in all 3 skills | `grep -c "not auto-loaded" skills/executing-plans/SKILL.md` | 0 | checked each of the 3 files |
| Independent two-pass review (reviewer subagent) | re-run: reviewer agent over `git diff` | 0 | PASS/PASS; findings 3 (deploy pending) + 4 (fixed) |

Full harness suite (`scripts/run-tests.sh`, same as the CI `harness-ci` job) was run twice —
after wave 1 and after the lint-comment fix — ALL GREEN, 150 python + hook contract tests.
Cited in prose per the strict-gate cap on whole-suite Verify rows.

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
