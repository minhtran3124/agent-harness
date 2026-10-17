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

### Review Minor findings (forwarded to final review)

- Task 1.1: `render_agent_definitions.py` writes agent files before the snapshot, so a skill with broken frontmatter leaves a partial render on exit 1.
- Task 1.1: the `--defaults-out` write is not atomic, and an absent parent folder raises an uncaught `FileNotFoundError`.
- Task 1.1: the frontmatter-value test uses only synthetic skills (no real skill declares `model`/`effort` today).
- Task 1.2: an inserted line uses LF even in a CRLF file (`scripts/apply_model_config.py:205`).
- Task 1.2: with duplicate `model:`/`effort:` keys, replace rewrites only the first; delete removes all.
- Task 2.1: `consumer_repo` registers its temp dir inside a command substitution, so `finish` never removes it (inherited `tests/lib.sh` pattern).
- Task 2.1: the agent fixture has no `effort:` line, so the hook test proves insert, not replace.
- Task 2.2: `new_target` has the same command-substitution cleanup leak in `tests/scripts/model-config-deploy.test.sh`.
- Task 2.2: the no-applier skip path is untested; its cleanup runs `rm -f "$DEPLOYED_LIST" ""` with an empty `MODELS_SNAPSHOT` under `set -e` (exit status unverified).
- Task 2.2: if the apply step fails after the check passes, the `ERR` trap exits before cleanup and the temp snapshot is left behind.
- Task 2.3: `bash scripts/lint-doc-truth.sh` fails until Task 3.1 adds `hooks/model-config.sh` to the CLAUDE.md hook table (the consumer-path failures cleared with Task 2.2).

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane evidence | `python3 .claude/scripts/verify_summary.py --lane model-effort-config` | 0 | intake-time check only | |

### Not auto-verified

- none

### Rollback

- `git revert <sha>` for each commit on `feat/model-effort-config` (filled with exact shas at ship).

### Harness-Delta

- backlog (Task 1.2): the worktree-isolation guard refuses compound shell commands (loops, `cd` then `git`), so implementers run each command alone.
