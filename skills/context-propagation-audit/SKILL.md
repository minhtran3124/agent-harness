---
name: context-propagation-audit
description: Audit workflow-as-code changes to prove each authoritative instruction reaches every isolated consumer context. Use for changed skills, dispatch prompts, agents, or rules; assumed delivery is a failure.
allowed-tools: Read, Write, Grep, Glob
---

# Context-Propagation Audit

Run only when the diff trips the `workflow-engine` hard gate in `harness-manifest.json`:
skills, skill dispatch/reviewer/scorer prompts, `agents/`, or `rules/`. It is a delivery oracle,
separate from runtime correctness and intent review.

## Audit matrix

For each changed instruction or policy, list every relying consumer and record:

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| authority | prompt/skill/agent | main, implementer, reviewer, scorer, new session | always-loaded, paths-triggered, pasted, explicit Read | test or inspected call site |

Find consumers with graph tools, then confirm every load-bearing claim against source with Grep or
Read. A no-consumer result is unknown unless it names the search surface. Main-session evidence never
proves delivery to a fresh child context.

## Fail conditions and repair

Fail when a load-bearing instruction is `assumed`/`unconfirmed`, child delivery is
inferred from main-session behavior, or an inline policy subset is unanchored. Prefer an explicit
Read; allow an inline copy only when complete and protected by a drift test. Do not flag a
complete pasted authority, an explicit Read, or a registry-linted copy.

Write the matrix and PASS/FAIL to `SUMMARY.md` under `### Context-Propagation Audit`. List and
repair each failed row; route an unfixable Rule-4 issue to `ESCALATIONS.md`. A standalone audit
returns the same matrix inline. Keep the known escape probes in
`evals/skills/review-chain/fixtures/context-rule-unread/` and
`evals/skills/review-chain/fixtures/stale-inline-policy/`.

`subagent-driven-development` runs it before correctness review only when the trigger fires.
Workflow-engine changes are high-risk at intake; do not lower the lane to skip it.
