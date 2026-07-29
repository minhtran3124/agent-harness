---
name: context-propagation-audit
description: Audit workflow-as-code changes to prove each authoritative instruction reaches every isolated consumer context. Use for changed skills, dispatch prompts, agents, or rules; assumed delivery is a failure.
---

# Context-Propagation Audit

Run only when the changed diff trips the `workflow-engine` hard gate in `harness-manifest.json`:
skills, skill dispatch/reviewer/scorer prompts, `agents/`, or `rules/`. It is a delivery oracle,
separate from runtime correctness and intent review.

## Audit matrix

For each changed instruction or policy, enumerate every relying consumer and record:

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| authority | prompt/skill/agent | main, implementer, reviewer, scorer, new session | always-loaded, paths-triggered, pasted, explicit Read | test or inspected call site |

Use graph tools to find consumers, then corroborate every load-bearing claim against source with
grep/read. A no-consumer result is unknown unless it names the search surface. Main-session
evidence never proves a fresh child context.

## Fail conditions and repair

Fail the audit when a load-bearing instruction is `assumed`/`unconfirmed`, child delivery is
inferred from main-session behavior, or an inline policy subset is unanchored. Prefer an explicit
Read; an inline copy is allowed only when complete and protected by a drift test. Do not flag a
complete pasted authority, explicit Read, or registry-linted copy.

Write the matrix and PASS/FAIL to `SUMMARY.md` under `### Context-Propagation Audit`. List each
failed row and repair; route an unfixable Rule-4 issue to `ESCALATIONS.md`. Standalone audits return
the same matrix inline. Preserve the known escape probes in
`evals/skills/review-chain/fixtures/context-rule-unread/` and
`evals/skills/review-chain/fixtures/stale-inline-policy/`.

The audit is invoked before correctness review by SDD only when the trigger fires. Workflow-engine
changes are high-risk at intake; do not lower the lane to bypass this proof.
