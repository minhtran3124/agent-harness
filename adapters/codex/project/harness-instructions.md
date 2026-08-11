# Agent Harness for Codex

This project uses the Agent Harness plugin for shared skills and lifecycle hooks. Project-scoped
agent profiles live under `.codex/agents/`; use their declared role rather than silently widening
their sandbox, network, MCP, nesting, or output policy.

Treat `agents/PROJECT.md` and the rule paths it names as project-owned sources of truth. Keep
generated adapter files separate from user-owned Codex configuration, and do not infer that hooks
are active merely because the plugin is installed: capability/trust checks run outside hooks.
