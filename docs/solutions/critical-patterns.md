# Critical Patterns

Always read when consuming this knowledge base, regardless of query domain. Keep this file short — entries here are high-leverage learnings that apply across many features.

Add an entry only when the pattern:
1. Has caused non-obvious bugs in multiple modules, OR
2. Documents a non-negotiable project rule that can't be expressed in a linter

## Entries

## [2026-06-11] meta-repo-signal-remapping
**Type:** knowledge
**Module:** skills/bootstrap-xia2
**Tags:** meta-repo, signal-remapping, project-md, dual-audience-docs, bootstrap-update-mode, hook-friction
**Applicable when:** Bootstrapping or updating xia2 PROJECT.md (or any risk-classification config) for a repo whose "application" is the tooling itself — skills, hooks, scripts.

A meta/harness repo does have high-blast files, security surfaces, and public contracts — they live in `settings.json`, `hooks/*.sh`, `tests/lib.sh`, `.mcp.json`, and hook-parsed template fields (`Lane:`), not in app code layers. Map each app-centric xia2 signal category to its harness-native analog instead of leaving it empty, grounded in churn + inbound-reference evidence.

**Full doc:** docs/solutions/harness-bootstrap/meta-repo-signal-remapping.md
---

## [2026-06-11] meta-repo-signal-remapping-decisions
**Type:** decision
**Module:** skills/bootstrap-xia2
**Tags:** meta-repo, signal-remapping, project-md, dual-audience-docs, bootstrap-update-mode, hook-friction
**Applicable when:** Bootstrapping, classifying risk, or sourcing conventions in a meta/harness repo whose `.claude/rules` docs describe the *target* projects it deploys into.

Two decisions: (1) `agents/PROJECT.md` convention sources point at `skills/README.md` + `rules/behavior.md` — not `.claude/rules/architecture.md`/`guidelines.md`, which describe the target FastAPI projects and would mislead agents working ON the harness; a maintainer note guards against re-bootstrap regression. (2) Non-applicable risk categories (DB sessions, auth) record "none" PLUS a named harness analog as a Deep trigger (warn↔block hook flips, secrets-scan edits, `.mcp.json` additions), preserving the category's protective intent.

**Full doc:** docs/solutions/harness-bootstrap/meta-repo-signal-remapping-decisions.md
---

<!--
Example entry shape:

## Async context propagation

**Applies to:** any background task spawning
**Rule:** Use `contextvars.copy_context()` when spawning; otherwise request-scoped state (user, tenant, trace_id) is lost.
**Reference:** docs/solutions/async/context-propagation.md
-->
