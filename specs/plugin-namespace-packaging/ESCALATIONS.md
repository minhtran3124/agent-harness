# plugin-namespace-packaging — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.

---

## E001

- raised_by: orchestrator (feature-intake)
- date: 2026-06-11
- trigger: hard-gate
- question: Hook registration model — keep hooks registered via settings.json (copied into target projects, current model) or move them to plugin hooks/hooks.json (ship with the plugin)?
- context: All packaging work blocked — this decides whether install-harness.sh still copies hooks/ + settings.json, or the plugin carries them.
- options:
  - A) Keep settings.json model — hooks stay project-level; plugin only namespaces skills. Least change, but two install surfaces (plugin for skills, installer for hooks/rules).
  - B) Move hooks to plugin hooks.json — single install surface (`/plugin install harness`), but hook paths/registration must be rewritten and tested; rules/templates still need a delivery path.
- default_if_no_response: BLOCK
- decision: A — keep settings.json model; plugin only namespaces skills
- decided_by: Minh Tran
- decided_at: 2026-06-11

## E002

- raised_by: orchestrator (feature-intake)
- date: 2026-06-11
- trigger: hard-gate
- question: Installer strategy — convert install-harness.sh fully to the plugin model, or keep it as a parallel "project-skill" install path alongside the plugin?
- context: install-harness.sh currently copies skills/agents/hooks/rules/templates/settings.json into target projects; plugin install replaces at least the skills part.
- options:
  - A) Plugin-only — deprecate the copy-skills part of the installer; installer shrinks to rules/templates/MCP wiring. Clean, single source of truth, but breaks existing installed projects until they migrate.
  - B) Dual path — keep the flat copy installer working AND add plugin packaging. No breakage, but bare-name vs namespaced skill duplication risk for users who install both ways.
- default_if_no_response: BLOCK
- decision: A — plugin-only for skills; installer shrinks to rules/templates/hooks/settings/MCP wiring
- decided_by: Minh Tran
- decided_at: 2026-06-11
