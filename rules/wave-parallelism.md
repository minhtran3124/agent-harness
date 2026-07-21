---
paths:
  - "specs/**/PLAN.md"
---

# Wave Parallelism Rule

Path-scoped (not auto-loaded): injected when a `specs/**/PLAN.md` file is read; wave
execution also loads it via the explicit Read step in `executing-plans` / `subagent-driven-development`.

Tasks in `specs/<slug>/PLAN.md` group into waves. Same-wave tasks run in parallel; wave N+1 waits for wave N.

Related: `plan-format.md`, `orchestration.md`.

## Invariants

1. **Zero file overlap** in same-wave tasks. Enforced at plan-write time per `plan-format.md` Guardrail 1.
2. **Synchronization at wave boundary** — all wave-N tasks must be green (`<verify>` exit 0) before wave N+1 starts.
3. **Fresh context per task** — each task in a wave spawns its own subagent with full token budget.
4. **Single parallel spawn** — orchestrator sends all wave-N subagent calls in ONE assistant message (parallel tool calls). Sequential spawning defeats the purpose.
5. **Collection before advance** — orchestrator aggregates summaries, updates PLAN task status, commits metadata, THEN starts wave N+1.

## Example (stack-neutral)

> Illustrative only — substitute your stack (see `techstacks/`).

| Wave | Tasks | Parallelism |
|------|-------|-------------|
| 1 | 1.1 data model + migration, 1.2 schemas | 2 parallel |
| 2 | 2.1 data-access layer | single |
| 3 | 3.1 service, 3.2 auth dependency | 2 parallel |
| 4 | 4.1 endpoint + wiring | single |
| 5 | 5.1 integration e2e | single |

Same-wave files are disjoint:
- Wave 1: 1.1 touches `models/` + migrations; 1.2 touches `schemas/` — no overlap.
- Wave 3: 3.1 touches `services/` + tests; 3.2 touches the auth-dependency file + tests — no overlap.

## Collection protocol

After a wave completes:

1. Read each subagent summary; verify every `<verify>` passed
2. Append task commit shas to PLAN.md `## 7. Status Log`
3. Append Rule 1–3 deviations to `specs/<slug>/SUMMARY.md` `### Deviations`
4. If any blocker → pause wave chain, update STATE.md with cursor, surface to user
5. Only then spawn next wave

## Orchestrator commit (per wave)

After collection, main thread creates one lightweight metadata commit:

```
chore: complete wave N for <slug>

Tasks: 1.1, 1.2
Commits: abc123, def456
```

Keeps git log readable as "wave boundaries" alongside task-level atomic commits.

## When to skip this overhead

Single-task waves don't need wave machinery — execute in main thread or as one subagent. The rule matters when ≥2 tasks share a wave. Plans with no parallelism (all tasks sequential) may omit the `(wave K)` heading suffix entirely (legacy XML plans: the `wave="K"` attribute) per `plan-format.md`.
