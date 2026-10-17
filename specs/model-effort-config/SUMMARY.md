# model-effort-config — Summary

Lane: high-risk
Confidence: medium
Reason: hard gates high-blast (new SessionStart hook in settings.json, hooks/*) and workflow-engine (skill and agent frontmatter, new loader skill)
Flags: existing behavior, public contracts, cross-platform, multi-domain
Affects: agents/runtime-bindings.json, scripts/render_agent_definitions.py, scripts/install-harness.sh, scripts/deploy-harness.sh, settings.json SessionStart hooks, skill frontmatter, Codex adapter
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/model-effort-config/intent.md @ 09bc03e9daf0892a15f96f284ec25bcbfb9fb229

> I am thinking of a settings file in YAML or JSON. In this file, I can configure the model and effort for each agent/skill/etc. We support 1 command or skill that loads these configurations into the current harness workflow. Make research to find similar patterns and best practices for it.

> - việc áp dụng các settings nãy sẽ dc apply khi user cài lần đàu tiên và new session
> - khi user thay đổi mode/effort ở giữa phiên thì sẽ tôn trọng ý định của user, ko cố gắng override ngược lại

> - (A) Phạm vi tách biệt
> - "/clear"dc tính là new session

> ok start with feature-intake

### Intake notes

- Confidence is medium, not high: the direction is settled by the user's decisions (apply at install and SessionStart `startup|clear`; respect mid-session `/model` and `/effort`; option A scope split), but the intent holds `(assumed)` defaults and three open questions for brainstorming and xia2.
- The hard gates are inherent to the request (a SessionStart hook is required by "apply at new session"), so the user approved the scope with the gates visible; no narrowing applies.
- Branch `feat/model-effort-config` was cut from `sdlc`; the eventual PR targets `sdlc`.
- 2026-10-17 xia2 go/no-go: A5 is false in print mode (research-brief.md probes 5, 6, 8, 9). The user chose option 1: accept that a hook-written agent change takes effect from the next session in headless runs. D9 and D11 are unchanged, so no `DC<n>` is needed; the `--apply` report and docs must state when each change takes effect.
- Prior research in chat: Claude Code honours `model`/`effort` in agent and skill frontmatter and the Agent tool `model` parameter; SessionStart exposes `source` matchers and a `reloadSkills` output; agent reload order after SessionStart is undocumented.

## What changed

Intake and brainstorming: intent approved; `design.md` approved by the user after five spec-review rounds (Approach 1, applier that rewrites deployed frontmatter; decisions D1–D13). No implementation yet.

### Rationale

Classified high-risk because the request requires a new SessionStart hook registration and edits to skill and agent definitions, both manifest hard gates.

### Alternatives considered

- Dispatch-time injection of `model`/`effort` on Agent calls: rejected; misses user-dispatched agents and skill effort, and applies mid-session (design.md Approaches).
- SessionStart re-running full deploy: rejected; slow and can stop on protected-file conflicts.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane evidence | `python3 .claude/scripts/verify_summary.py --lane model-effort-config` | 0 | intake-time check only | |

### Not auto-verified

- none

### Rollback

- `git revert <sha>` for each commit on `feat/model-effort-config` (filled with exact shas at ship).

### Harness-Delta

- none
