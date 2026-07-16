---
problem_type: knowledge
module: skills/bootstrap-xia2
tags: meta-repo, signal-remapping, project-md, dual-audience-docs, bootstrap-update-mode, hook-friction
severity: critical
applicable_when: Use this pattern when bootstrapping or updating xia2 PROJECT.md (or any risk-classification config) for a repo whose "application" is the tooling itself — skills, hooks, scripts — rather than an app codebase the default heuristics expect.
affects:
  - skills/xia2/PROJECT.md
  - agents/PROJECT.md
supersedes: null
confidence: high
confirmed_at: 2026-06-11
---
## Applicable When
Use this pattern when bootstrapping or updating xia2 PROJECT.md (or any risk-classification config) for a repo whose "application" is the tooling itself — skills, hooks, scripts — rather than an app codebase the default heuristics expect.

## Pattern
Harness-native analogs for application-centric risk signals — when bootstrapping `skills/xia2/PROJECT.md` for a meta/harness repo (no app framework, no DB, no auth, no dependency manifests), every xia2 signal category must be re-mapped from its application meaning to its harness equivalent rather than left empty or filled with FastAPI placeholders. The insight: a harness repo *does* have high-blast files, security surfaces, public contracts, and transaction-like semantics — they just live in hooks, settings, and template field names instead of code layers.

## How to Use
When filling PROJECT.md for this repo (or any skills/hooks harness), apply this mapping table:

- High-blast files → `settings.json` (hook registration; 14 inbound refs — one line wires/unwires automation), `hooks/*.sh` (auto-run on every trigger in every session of every consuming repo), `tests/lib.sh` (sourced by all 12 `*.test.sh` suites), `skills/visual-planner/render_plan.py` (deterministic core engine).
- Dependency manifest → `.mcp.json` is the only dep-like file (declares the `code-review-graph` MCP server via `uvx`); adding MCP servers is a Deep trigger.
- Session/transaction primitive → hook fail-open vs fail-closed semantics (e.g. `RISK_CORROBORATION_STRICT=1`); flipping a hook between warn and block is the harness equivalent of changing DB session scoping.
- Auth surface → the `commit-quality-gate.sh` secrets scan; weakening it is the security-relevant change.
- Public API contract → skill invocation names in `skills/*/SKILL.md` frontmatter, the `settings.json` hook-registration shape, and template field names hooks parse programmatically (`Lane:`, `Confidence:`, `### Verify`, `### Rollback` — `risk-corroboration.sh` greps `Lane:`).

Ground the mapping in evidence, not intuition: git churn (top-25 over 6 months), grep-based inbound-reference counts (settings.json 14, tests/lib.sh 14, render_plan.py 9), the repo's own `rules/auto-correct-scope.md` Rule-4 high-blast list, and `harness-ci.yml`.

## Code Example
```bash
# Inbound-reference count as high-blast evidence:
grep -rl "settings.json" docs/ hooks/ tests/ | wc -l   # → 14 refs ⇒ high-blast
# Contract field a hook parses (changing the field name breaks the harness):
grep "Lane:" hooks/risk-corroboration.sh
```

## Gotchas
- When PROJECT.md exists but is an unfilled template (placeholders like `<your project name>` + FastAPI example entries), "Update mode" degenerates to a full fill-in: there is nothing to diff (no stale/consistent entries), so the `.proposed` output is effectively an Init render — but the never-overwrite rule still applies; originals are not touched.
- `blast-radius-check.sh` will fire on `.proposed` writes when they are not in the active plan's `<files>` set. This is intentional skill output, not scope creep — note it and proceed; do not widen the plan to silence it.
- Structural scaffolding is create-if-missing: `specs/README.md` and `specs/STATE.md` were created; existing `docs/solutions/*` and `agent-memory/README.md` were correctly skipped.

## Related
- docs/solutions/harness-bootstrap/meta-repo-signal-remapping-decisions.md
