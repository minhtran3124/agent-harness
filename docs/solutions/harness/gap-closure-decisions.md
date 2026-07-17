---
problem_type: decision
module: hooks/commit-workflow
tags: ground-truth, research-docs, gap-closure, dormant-hook, settings-json, rule-4, workflow
severity: standard
applicable_when: When implementing a backlog item named in a research/planning doc, or when adding a new hook and deciding whether to activate it in the same change.
supersedes: null
confidence: high
confirmed_at: 2026-07-17
affects:
  - docs/research-openai-harness-engineering.md
  - hooks/protected-path-guard.sh
  - settings.json
---

## Applicable When
When implementing a backlog item named in a research/planning doc (verify it still applies), or when adding a new hook and deciding whether to wire it in the same change.

## Decision 1
### Context
Gap-closure work driven by `docs/research-*.md`, which named a backlog of "missing" harness features to implement. Before building, the question was how much to trust those research docs as ground truth for what does and doesn't already exist in the repo.
### Options Considered
- **Option A:** Trust the research docs — treat each named gap as genuinely missing and implement directly. Faster to start; no verification step.
- **Option B:** Verify each named gap on disk first (grep/read the actual repo), then build only what is genuinely absent. Adds a per-gap verification cost up front but prevents wasted re-implementation.
### Decision & Rationale
Chose **Option B** — verify each gap on disk before implementing. The deciding factor: a research doc reflects the repo state at the moment it was written, and this repo moves faster than the research captures it. Concretely, the majority of "gaps" were already shipped — `verify_summary.py`, the read-only `reviewer` agent, the SessionStart `session-knowledge` hook, the Q3 `Affects:` contract field, `ci-strict-gate.sh`, and the entire `benchmarks/review-chain` infra. Building from the doc alone would have re-implemented all of these.
### Applicable When
A future engineer is about to implement a backlog item named in a research or planning doc (`docs/research-*.md`, a gap-closure plan, a stale spec) that asserts a feature is missing — verify presence on disk before writing code.
### Consequences
Enables: the real remaining work was a small fraction of the documented backlog; avoided re-implementing already-shipped features across ~5 phases. Constrains: every doc-named gap now carries a mandatory on-disk verification step before it can be actioned (slower to start, cheaper overall). The cross-session memory `research-docs-predate-repo` records the underlying observation; this is the decision/protocol derived from it.

## Decision 2
### Context
A new hook, `hooks/protected-path-guard.sh`, was added to guard protected paths. The hook only takes effect once registered in `settings.json` under a trigger key. The question was whether to wire it into `settings.json` in the same change or ship it unregistered (dormant).
### Options Considered
- **Option A:** Wire immediately — register the hook in `settings.json` as part of this change. Feature is live at once, but the change alters runtime behavior for every session.
- **Option B:** Ship dormant — land the hook script + test unregistered, leave `settings.json` wiring as a separate later step. No runtime behavior changes now; activation is a distinct, explicit action.
### Decision & Rationale
Chose **Option B** — ship dormant. Editing `settings.json` hook registration is itself a Rule-4 / high-blast change (per `rules/auto-correct-scope.md`: "Changes to high-blast-radius files: settings.json (hook registration)") that needs explicit human confirmation. Shipping dormant changes no runtime behavior, keeps the hook landing inside the autonomous lane, and matches the established `auto-test-on-change` precedent (present on disk, unregistered).
### Applicable When
A future engineer adds a new hook (or other `settings.json`-registered automation) and must decide whether to activate it in the same change — default to shipping dormant and splitting the `settings.json` wiring into a separate Rule-4-gated step.
### Consequences
Enables: the hook + its test land autonomously with zero runtime-behavior change and zero `settings.json` edit; the CLAUDE.md hook table marks it `⬜ dormant`. Constrains: the hook does nothing until a follow-up human-confirmed step wires it in — there is now a tracked pending activation, and a dormant hook with no scheduled wiring can be forgotten.

## Related
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md
