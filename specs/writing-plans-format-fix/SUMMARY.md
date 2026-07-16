# writing-plans-format-fix — Summary

Lane: high-risk
Confidence: high
Reason: v2 direction touches two Rule-4 high-blast surfaces (hooks/blast-radius-check.sh, skills/visual-planner/render_plan.py). The hard gate is satisfied by an explicit user directive (2026-07-16) quoted in Intent; direction unambiguous.
Flags: high-blast (hooks/*, render_plan.py)
Affects: plan-format contract (rules/plan-format.md + all its consumers: writing-plans, executing-plans, render_plan.py, blast-radius-check.sh, plan-document-reviewer-prompt)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Turn 1: "from docs/reviews/over-engineering-review-2026-07-16.md
check C1. writing-plans teaches a plan format its own downstream gate rejects ✅ — HIGH
research and review all aspects of the problem, create design + plan for it"

Turn 2 (scope-deciding directive): "hiện tại ko bắt buộc viết plan bằng xml nữa, hãy sửa writing plan + executing plan + render plan to html."
(= XML is no longer mandatory for plans; fix writing-plans + executing-plans + render-plan-to-HTML accordingly.)

## What changed

Research + design v1 (dedup-to-XML) completed for C1; user then redirected twice: first "XML optional" (design v2, dual syntax), then "purge XML from plan generation" (wave 4). Final state: **one semantic schema (id/wave/files/action/verify/done + unchanged guardrails); markdown `### Task` + field-bullet syntax is the ONLY authoring format; XML demoted to legacy read-only** (19 existing plans keep rendering/executing, zero migration; extending an XML plan keeps XML since mixed files parse XML only). Implementation: render_plan.py (markdown parser + wave-3 scanner hardening — inline-code masking + per-fence fallback fixed the pre-existing "plan parses to 0 tasks" bug), executing-plans Step-0 (semantic checks), writing-plans + reviewer prompt (markdown-only, checkbox format deleted — the original C1 fix), rules/plan-format.md (single markdown Task Schema + Legacy XML section), blast-radius-check.sh (reads `- **Files:**` bullets), plus hook tests.

### Rationale

The user's directive removes the XML mandate but the semantic contract (fields, waves, guardrails) is what downstream tooling actually needs — so the design keeps the schema and relaxes only the syntax. Canonical home stays rules/plan-format.md (preserves the C1 dedup fix); render parser is fallback-only so the XML path is untouched by construction.

### Alternatives considered

- Markdown-only (deprecate XML): rejected — 19 existing plans + At-a-glance pipeline would need migration for zero benefit.
- Free-form plans (no task schema at all): rejected — executing-plans, wave parallelism, blast-radius, and At-a-glance all consume the fields; dropping the schema kills those consumers, far beyond the directive.
- Design v1 (dedup toward mandatory XML): superseded by the user directive.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| render hook tests (markdown tasks, prose-heading filter, backtick-prose) | `bash tests/hooks/render-plan-on-write.test.sh` | 0 | 8 passed |
| blast-radius tests (markdown + mixed Files sets) | `bash tests/hooks/blast-radius-check.test.sh` | 0 | 12 passed |
| doc-truth lint (paths + hook table) | `bash scripts/lint-doc-truth.sh` | 0 | clean |
| legacy XML plan still parses (was 0 tasks pre-fix) | `python3 skills/visual-planner/render_plan.py specs/plan-at-a-glance/PLAN.md /tmp/vs-paag.html > /tmp/vs-paag.out 2>&1 && grep -q "tasks=6 waves=5" /tmp/vs-paag.out` | 0 | wave-3 scanner fix |
| old checkbox format purged from skills | `grep -rq -e "Bite-Sized" -e "Plan Document Header" -e "Step 1: Write the failing test" skills` | 1 | no match = purged (C1) |
| no authoring doc offers XML as a choice | `grep -rq -e "equally valid" -e "either accepted syntax" -e "two syntaxes" skills rules` | 1 | no match = markdown-only |
| canonical rule defines the markdown Task Schema | `grep -q -e "### Task 1.1 — Short human title (wave 1)" rules/plan-format.md` | 0 | wave-4 |
| legacy XML support stays documented | `grep -q "Legacy XML plans (read-only support)" rules/plan-format.md` | 0 | 19 plans, zero migration |
| executing-plans gate is semantic, not syntax-bound | `grep -q "reject it for missing semantics" skills/executing-plans/SKILL.md` | 0 | Step-0 rewrite |
| stale worktree claim gone from writing-plans | `grep -q "created by brainstorming skill" skills/writing-plans/SKILL.md` | 1 | no match = fixed |
| full suite (L1 syntax + doc-truth + manifest + hook suites + L2 python) | `bash scripts/run-tests.sh` | 0 | ALL GREEN |
Verified: 2026-07-16T19:17:56

Session-only evidence (not re-runnable in CI, recorded for the audit trail): XML render
regression — `specs/intent-review-stage` PLAN.html byte-identical between the pre-change
baseline and the new parser; old-vs-new (`e4285f8`) task-count sweep over all 20
`specs/*/PLAN.md` shows plan-at-a-glance (0→6) as the only change; markdown demo plan
end-to-end (render + `--summarize` + `--emit-files`) gave tasks=3 waves=2 with correct
files JSON; local `.claude/rules/plan-format.md` synced byte-identical (gitignored,
absent on CI).

### Rollback

- Spec artifacts: `git rm -r specs/writing-plans-format-fix/` or revert their commit.
- Implementation: `git revert` of the task commits on the feature branch — prose + one fallback parser + one hook grep extension; no data/schema migration. XML path in render_plan.py untouched, so reverting restores the exact prior behavior.

### Harness-Delta

- The skill chain's own reviewer prompt enforced the correct format while its parent SKILL.md taught the wrong one — reviewer prompts and parent skills have no consistency check; candidate for /compound.
- A format mandate lived in 5+ documents; relaxing it required touching all of them — supports issue #67 Phase 3 (one canonical home per fact).
