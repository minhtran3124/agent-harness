# Agent Harness

This project uses the Agent Harness for shared skills, lifecycle hooks, and governance rules.
Project-scoped agent profiles live under `.codex/agents/`; use their declared role rather than
silently widening their sandbox, network, MCP, nesting, or output policy.

Treat `agents/PROJECT.md` (if present) and the rule paths it names as project-owned sources of
truth. Keep generated adapter files separate from user-owned configuration, and do not infer that
hooks are active merely because the plugin is installed: capability/trust checks run outside hooks.

The rules below are always-on: apply them in every session. The on-demand rules listed at the end
apply only when their globs match the files you are working on.
