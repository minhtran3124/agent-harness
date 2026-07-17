# phase2-wave3 — Summary

Lane: high-risk
Confidence: high
Reason: Diff touches templates/ (stack-profile deletion) which is in ci-strict-gate HARD_GATE_RE — high-risk forced mechanically. All four Wave-3 items were owner-decided (AskUserQuestion, 2026-07-17), so direction is unambiguous.
Flags: high-blast (templates/ via strict gate)
Affects: templates/stacks/ (3 profiles removed), agents/PROJECT.md (filled for this repo)
Input-type: harness improvement

### Intent

Wave 3 of Phase 2. Owner decisions (2026-07-17): cut templates/stacks/{nextjs,node,django}; promote the .proposed agents/PROJECT.md render; keep protected-path-guard dormant; keep agent-memory. This spec executes the two actionable choices.

## What changed

Removed the three bundled stack profiles that bootstrap-xia2 has no detection marker to reach (nextjs, node, django) — fastapi + _skeleton remain, and the never-emit-wrong-stack fallback keeps JS/Django consumers functional. Promoted `.claude/agents/PROJECT.md.proposed` (bootstrap-rendered, accurate for this repo — correct test command, source→test mapping, and the note that .claude/rules/architecture.md describes target FastAPI projects not this repo) into the tracked `agents/PROJECT.md`, stripping the `<!-- auto -->` review annotations. The two keep-decisions (protected-path-guard, agent-memory) required no change — recorded here for the audit trail.

### Rationale

Each item was a product/decision call, not a technical one — the deep review (PR #77) had already established the mechanics. Cut-vs-keep for stacks turned on distribution intent (owner: cut); PROJECT.md on a shipping trade-off (owner: promote, accepting meta-repo facts in the payload). Keeping the guard dormant and agent-memory avoids reversing recorded decisions / rewording linted docs for near-zero gain.

### Alternatives considered

- Keep all stacks (distribution breadth): owner chose cut — no in-repo consumer, 2 of 3 unreachable by detection.
- Untrack PROJECT.md from payload instead of promoting: owner chose promote — execution agents read it and it was already rendered.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| plan parses (markdown, 3 tasks / 2 waves) | `bash -c 'python3 skills/visual-planner/render_plan.py specs/phase2-wave3/PLAN.md /tmp/p2w3.html > /tmp/p2w3.out 2>&1 && grep -q "tasks=3 waves=2" /tmp/p2w3.out'` | 0 | |
| stacks cut, fastapi+skeleton kept | `bash -c 'test ! -d templates/stacks/nextjs && test ! -d templates/stacks/node && test ! -d templates/stacks/django && test -d templates/stacks/fastapi && test -d templates/stacks/_skeleton'` | 0 | |
| PROJECT.md filled, annotations stripped | `bash -c '! diff -q agents/PROJECT.md agents/PROJECT.template.md && grep -q "bash scripts/run-tests.sh" agents/PROJECT.md && ! grep -q "auto:" agents/PROJECT.md'` | 0 | no longer template-identical |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | clean |
| full suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN |

### Rollback

- `git revert <commit>` — restores the 3 stack profiles and the template-identical PROJECT.md from history; no data/schema migration.

### Harness-Delta

- none
