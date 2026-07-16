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

Research + design v1 (dedup-to-XML) completed for C1; user then redirected: XML optional. Design v2 adopted: **one semantic schema (id/wave/files/action/verify/done + unchanged guardrails), two accepted syntaxes** — a new markdown `### Task` + field-bullet syntax as the taught default, XML fully retained (19 existing plans, zero migration). Implementation updates render_plan.py (markdown fallback parser, same return contract), executing-plans Step-0 (semantic, syntax-neutral checks), writing-plans + its reviewer prompt (teach markdown, drop the superpowers checkbox format — the original C1 fix), rules/plan-format.md (canonical dual-syntax definition), blast-radius-check.sh (reads `- **Files:**` bullets), plus hook tests.

### Rationale

The user's directive removes the XML mandate but the semantic contract (fields, waves, guardrails) is what downstream tooling actually needs — so the design keeps the schema and relaxes only the syntax. Canonical home stays rules/plan-format.md (preserves the C1 dedup fix); render parser is fallback-only so the XML path is untouched by construction.

### Alternatives considered

- Markdown-only (deprecate XML): rejected — 19 existing plans + At-a-glance pipeline would need migration for zero benefit.
- Free-form plans (no task schema at all): rejected — executing-plans, wave parallelism, blast-radius, and At-a-glance all consume the fields; dropping the schema kills those consumers, far beyond the directive.
- Design v1 (dedup toward mandatory XML): superseded by the user directive.

### Deviations

- none (pending execution)

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Ground truth: 19/19 task-bearing plans XML, 0 checkbox | `for f in specs/*/PLAN.md; do grep -q '<task ' "$f" && echo XML; done \| wc -l` | 0 | research phase |
| Old-format echoes outside writing-plans | `grep -rn "Bite-Sized\|Plan Document Header\|Write the failing test" skills/ rules/ \| grep -v writing-plans/SKILL.md` | 0 | single echo: executing-plans:67 |
| PLAN.md v2 renders (format self-check) | auto: `render-plan-on-write.sh` on save | 0 | PLAN.html + At-a-glance regenerated |

| render hook tests incl. 2 new markdown cases | `bash tests/hooks/render-plan-on-write.test.sh` | 0 | 7 passed |
| blast-radius tests incl. 3 new markdown/mixed cases | `bash tests/hooks/blast-radius-check.test.sh` | 0 | 12 passed |
| markdown plan end-to-end (render + At-a-glance + emit-files) | `python3 skills/visual-planner/render_plan.py <scratch>/mdplan/PLAN.md [--summarize\|--emit-files]` | 0 | tasks=3 waves=2; files JSON correct |
| XML path untouched (regression) | `diff <baseline> <after>` on specs/intent-review-stage render | 0 | byte-identical |
| writing-plans markers gone + canonical pointer | task 1.2 `<verify>` greps | 0 | PASS |
| executing-plans syntax-neutral | task 1.3 `<verify>` greps | 0 | PASS |
| plan-format.md dual-syntax canonical | task 1.4 `<verify>` greps | 0 | PASS |
| full suite (L1 syntax + doc-truth + manifest + hook tests + L2 python) | `bash scripts/run-tests.sh` | 0 | ALL GREEN (173 passed, 1 skipped + all hook suites) |
| wave 3: backtick/quoted tag prose can't zero a plan | `bash tests/hooks/render-plan-on-write.test.sh` | 0 | 8 passed (new backtick-prose case) |
| wave 3: plan-at-a-glance recovers | `python3 skills/visual-planner/render_plan.py specs/plan-at-a-glance/PLAN.md <out>` | 0 | tasks=6 waves=5 (was 0) |
| wave 3: no other plan's count changed | old (e4285f8) vs new parser sweep over `specs/*/PLAN.md` | 0 | only plan-at-a-glance changed (0→6) |
| wave 3: deployed rules copy synced | `diff rules/plan-format.md .claude/rules/plan-format.md` | 0 | byte-identical (user-authorized) |
| wave 3: full suite re-run | `bash scripts/run-tests.sh` | 0 | ALL GREEN |

### Rollback

- Spec artifacts: `git rm -r specs/writing-plans-format-fix/` or revert their commit.
- Implementation: `git revert` of the task commits on the feature branch — prose + one fallback parser + one hook grep extension; no data/schema migration. XML path in render_plan.py untouched, so reverting restores the exact prior behavior.

### Harness-Delta

- The skill chain's own reviewer prompt enforced the correct format while its parent SKILL.md taught the wrong one — reviewer prompts and parent skills have no consistency check; candidate for /compound.
- A format mandate lived in 5+ documents; relaxing it required touching all of them — supports issue #67 Phase 3 (one canonical home per fact).
