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

then, after the research doc (`docs/research/harness-review-improvements/2026-07-21-dynamic-rule-loading-research.md`) was delivered with a per-rule recommendation and phasing:

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

- PR review fix (Codex P1, PR #141) — `implementer-prompt.md` referenced `auto-correct-scope.md` without instructing a Read; since implementers get pasted task text (never read specs/**), the path-scoped rule would never load in their context. Added an explicit "Read it FIRST" instruction to the template. Other dispatch templates checked: plan-document-reviewer reads the PLAN file (paths: triggers), correctness-reviewer inlines the Rule 1–4 definitions — no change needed.
- PR review fix (Codex P2, PR #141) — correction to the above: the correctness reviewer's inline Rule-4 list was a subset (5 of 8 STOP cases, missing session-scope, high-blast files, replacing a service), and being plan-blind it never reads specs/** to auto-load the rule. Completed the inline STOP list and added an explicit Read of `.claude/rules/auto-correct-scope.md` in both `correctness-reviewer-prompt.md` (dispatch path) and `correctness-review/SKILL.md` (standalone/main-thread fix-routing path).

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

#### Post-deploy end-to-end verification (2026-07-21)

After `bash scripts/deploy-harness.sh --yes` synced the `paths:` frontmatter into
`.claude/rules/` (7 rules, 12 hooks), a mock project mirroring the **deployed** rule files
(with per-rule canary markers) was probed with three headless `claude -p` runs on v2.1.216.
Canaries: `behavior`/`orchestration` (always-on controls); `plan-format`/`wave-parallelism`
(`paths: specs/**/PLAN.md`); `auto-correct-scope` (`paths: specs/**`).

| Case | Action | Canaries loaded | Expected? |
| --- | --- | --- | --- |
| T1 baseline | no file read | behavior, orchestration | ✅ 3 scoped rules absent at session start |
| T2 | Read `specs/mock-feature/PLAN.md` | + plan-format, wave-parallelism, auto-correct-scope | ✅ `specs/**/PLAN.md` + `specs/**` both match |
| T3 | Read `specs/mock-feature/SUMMARY.md` (non-PLAN) | + auto-correct-scope only | ✅ `specs/**` matches; PLAN-only globs correctly do NOT |

Proves the tiered semantics on the real deployed files: scoped rules stay out of the
session-start payload (~15 KB / ~55% saved), `specs/**/PLAN.md` rules load only for PLAN
operations, and the broader `specs/**` rule loads for any spec file. Repro:
`scratchpad/mock-run` (ephemeral). Note: the deploy writes gitignored `.claude/`; the tiered
behavior takes effect from the next Claude Code session in a repo (a restart), which is why
the isolated `claude -p` probes — reading the freshly-synced `.claude/rules/` — reflect it.

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
