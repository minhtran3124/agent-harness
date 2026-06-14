# rules-stack-agnostic — Summary

Lane: high-risk
Confidence: medium
Reason: 4 risk flags (public-contract, existing-behavior, weak-proof, multi-domain) and it redefines a core governance architecture (the rules/ layer) consumed by lint-doc-truth + CLAUDE.md + skills; likely touches the high-blast run-tests.sh / doc-truth CI contract.
Flags: public-contract, existing-behavior, weak-proof, multi-domain
Affects: rules/ governance layer (shared contract) + skills/bootstrap-xia2 + xia2/PROJECT.md (+ scripts/lint-doc-truth.sh / scripts/run-tests.sh if paths move)
Input-type: harness improvement
Route: high-risk full chain — /brainstorming (resolve the design fork) → /xia2 → /writing-plans → /subagent-driven-development → /compound (record the architecture decision)
Escalate: yes — confidence medium on a high-risk task; a real design fork (xia2/PROJECT.md vs rules/stacks/) must be resolved with the human in /brainstorming before implementation. Linear: MIN-25.

### Intent

<!-- The user's request VERBATIM at intake. -->

"create new linear ticket with purpose that refactor the rule architecture in folder rules/. because now it's only focus on BE. we can not use it in the FE repo or BE with node or another language"

(Tracked as Linear MIN-25, project harness-skills. Goal: the `rules/` layer must be reusable across FE repos, Node/TypeScript backends, and other languages — not Python/FastAPI-only.)

## What changed

<!-- Filled at execution time. -->

(Not started — intake only.)

### Rationale

High-risk because the refactor spans the rules/ governance layer (a shared contract) plus bootstrap-xia2, xia2/PROJECT.md, and the doc-truth/CI scripts — and it redefines how stack-specific guidance is carried. The goal is clear; the structure is a genuine design fork, so the high-risk chain front-loads /brainstorming as the human design checkpoint rather than blocking with a separate escalation.

### Alternatives considered

- Treat as `normal` lane / direct refactor: rejected — it changes a shared contract across multiple harness components with an unresolved structural fork; that is high-risk by both flag count and architecture-redefinition.

### Deviations

- none (intake only)

### Verify

<!-- Filled at execution time. Acceptance (from MIN-25): coupling grep = 0 on the universal rule set; FastAPI guidance preserved (relocated, nothing lost); CI/lint green. -->

<!-- Commands are pipe-free + idempotent so ci-strict-gate's verify_summary.py --check re-runs them clean. -->

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| full suite + doc-truth lint | `bash scripts/run-tests.sh` | 0 | ALL GREEN (102 passed, 1 skipped); lint green |
| lane evidence (dogfood) | `python3 scripts/check_lane_evidence.py rules-stack-agnostic` | 0 | high-risk SUMMARY has Verify + Rollback |
| plan format valid | `python3 scripts/check_plan_format.py specs/rules-stack-agnostic/PLAN.md` | 0 | XML schema valid; no story-size warning |

Also verified manually (pipe/grep, not table-re-runnable): both `rules/` skeletons carry 0 coupling tokens; `git show 09b74e8:rules/{architecture,guidelines}.md` diffs empty against `templates/stacks/fastapi/` (nothing lost); throwaway `deploy-harness.sh --target` ships a valid `.claude/rules/` + fastapi profile; final `/correctness-review` clean + `/intent-review` resolved.

### Deviations

- Review-driven (spec): genericized untagged stack tokens in `rules/auto-correct-scope.md` Rule 4 (session-scope, data-access base) — commit `5329ef1`.
- Review-driven (intent): genericized `requirements.txt`/`ruff`/`mypy` in `rules/auto-correct-scope.md` Rule 3 — commit `1b68006`.
- Review-driven (quality): created `templates/stacks/_skeleton/` as the concrete skeleton-fallback source + fixed the scaffolding-table base caveat — commit `7964c22`.

### Rollback

- Revert the branch commits: `git revert 1b68006 7964c22 5329ef1` (rules/ content is reversible markdown; no data/schema change). Or drop the branch entirely — `feat/rules-stack-agnostic` is not merged.

### Harness-Delta

- none — the workflow ran clean end-to-end (intake → brainstorm → xia2 → plan → execute → correctness + intent review).
