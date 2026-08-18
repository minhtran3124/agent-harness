---
decision: hybrid
fallback: direct
cli_version: 0.147.0
matrix: specs/codex-support/capability-matrix.json
hybrid_evidence: specs/codex-support/evidence/codex-0.147.0/packaging-hybrid.json
direct_evidence: specs/codex-support/evidence/codex-0.147.0/packaging-direct.json
runtime_evidence: specs/codex-support/evidence/codex-0.147.0/packaging-hybrid-runtime.json
runtime_execution: observed
fallback_trigger: Probe direct sync if Phase 5 cannot trust and load plugin skills/hooks; select it only after its own evidence passes.
---

# Codex packaging decision

Select the **hybrid** boundary for Phase 5: a plugin owns reusable skills and hooks, while the
project adapter owns `.codex/agents/*.toml`, runtime state, and bounded `AGENTS.md` integration.
Direct project sync remains the explicit fallback.

## Ownership boundary

- Plugin-owned: reusable skills, `hooks/hooks.json`, plugin manifest, and marketplace lifecycle.
- Project-adapter-owned: custom agents, runtime state, and non-clobber repository instructions.
- User-owned: existing root `AGENTS.md`, local customizations, trust choices, and unrelated Codex
  configuration.

## Executable evidence

On Codex CLI 0.147.0, the isolated local probe added and listed a marketplace, discovered and
installed the hybrid plugin, inspected its cached skill/hook files, verified an unchanged single
cache after reinstall, refreshed changed local content through remove/re-add, and removed all
created plugin state. It also proved strict parsing by rejecting an unknown configuration key and
parsing an empty valid configuration through to the expected non-terminal boundary. HOME and
CODEX_HOME were fresh, distinct temporary roots.

Phase 5 then invoked the installed plugin skill, executed the generated plugin hook, and dispatched
the generated project agent in one disposable model-backed session. Hook execution used Codex's
explicit automation trust-bypass flag against probe-generated, locally vetted hook source; the
evidence does not claim persisted user hook trust.

The direct candidate is deliberately recorded as `unknown`. Phase 2 materialized its representative
project files but did not observe Codex discover them and did not run a real direct-sync conflict
installer. Its evidence names Phase 5 as owner and defines the probe needed to make it selectable.

The CLI stores this local plugin under manifest version `0.0.1`; it does not use the `local` cache
segment currently described by the builder documentation. The probe therefore discovers exactly
one installed version directory rather than hard-coding its name. `marketplace upgrade` is Git-only,
so the offline local-source probe uses remove/re-add for refresh.

## Unresolved gaps

This evidence supports an advisory local distribution lifecycle and observed runtime execution on
the pinned macOS/CLI combination. It does not prove persisted user hook trust, the ChatGPT desktop
UI, other platforms, or a networked Git marketplace. Those claims must not be inferred from the
local probe.

The historical `feature/plugin-namespace-packaging` branch was inspected as pattern evidence only;
its Claude-specific `.claude-plugin` implementation was not reused.

## Fallback trigger

Switch Phase 5 to direct project sync without changing semantic-core contracts only after a
disposable direct-adapter probe has made that candidate selectable by proving project-level skill,
agent, and hook discovery plus real installer conflict behavior. Trigger that probe when the hybrid
runtime cannot both (1) discover/invoke installed plugin skills and (2) trust and execute installed
plugin hooks without mutating unrelated user state. Until direct passes, hybrid failure blocks the
adapter decision rather than silently selecting unproved fallback evidence.
