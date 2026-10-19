# Intent: Per-agent and per-skill model and effort configuration

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

The model and effort of each agent role is set only in `agents/runtime-bindings.json`, a
maintainer-edited file that is rendered into agent frontmatter at deploy time and never deployed to
consumers. Skills have no model or effort setting. A user cannot choose model and effort per
agent or skill in one settings file and load it into the harness workflow.

## Proposed outcome

- One settings file in JSON configures the model and effort for each agent and skill.
- One command or skill loads this configuration into the harness workflow.
- The settings are applied when the user installs the harness for the first time and when a new
  session starts. `/clear` counts as a new session (SessionStart `startup` and `clear`).
- When the user changes the model or effort in the middle of a session, the harness respects that
  intent and does not try to override it back.
- Scope split (option A): the configuration governs subagents and skills only. `/model` and
  `/effort` govern the main thread. The harness never writes the main session's model or effort.

## Affected users and systems

- Harness maintainers and consumer-repo users who choose models and effort levels.
- `agents/runtime-bindings.json`, `scripts/render_agent_definitions.py`,
  `scripts/install-harness.sh`, `scripts/deploy-harness.sh`, a new SessionStart hook entry in
  `settings.json`, skill frontmatter, and a new loader command or skill (assumed).
- The Codex adapter, which renders from the same bindings (assumed).

## Constraints

- JSON, not YAML: the repo has no YAML dependency.
- Extend the existing bindings source of truth instead of adding a competing file (assumed).
- Do not apply the configuration on SessionStart `resume`, `compact`, or `fork`.
- Do not register a `PreModelSwitch` hook.
- Do not write `model` or `effortLevel` into any settings file.
- Validate strictly: Claude Code silently ignores unknown frontmatter fields (assumed).
- Review roles keep a minimum effort floor so a profile cannot silently weaken review (assumed).
- A hook never reads a gitignored, agent-writable override for a gate decision
  (`docs/solutions/harness/gate-config-must-read-index.md`) (assumed).

## Out of scope

- Changing the main session's model or effort.
- Blocking or reverting a user's `/model` or `/effort` change.
- Choosing which concrete models each role should use by default (assumed).

## Open questions

- Does Claude Code reload agent definitions written by a SessionStart hook in the same session,
  or only in the next session? Skills have `reloadSkills`; agents are not documented.
- Do consumers get the user override layer, given that the bindings deliberately do not deploy
  today?
- Is the loader a skill, a script, or both, and what is its name (`/harness-models` proposed)?

## What success looks like

- After a first install, and after `startup` or `/clear`, every configured agent and skill
  carries the configured model and effort in its frontmatter.
- A `/model` or `/effort` change in the middle of a session stays in effect for that session.
- An invalid settings file fails with a clear error and changes nothing.
- The loader shows the effective model and effort per target and where each value came from.

## Original request

> I am thinking of a settings file in YAML or JSON. In this file, I can configure the model and effort for each agent/skill/etc. We support 1 command or skill that loads these configurations into the current harness workflow. Make research to find similar patterns and best practices for it.

> - việc áp dụng các settings nãy sẽ dc apply khi user cài lần đàu tiên và new session
> - khi user thay đổi mode/effort ở giữa phiên thì sẽ tôn trọng ý định của user, ko cố gắng override ngược lại

> - (A) Phạm vi tách biệt
> - "/clear"dc tính là new session

> ok start with feature-intake
