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

- Fix round (Task 2.3 file, found by Task 3.1's SC-21): `skills/harness-models/SKILL.md` mode words changed from code spans to quoted text, because `scripts/check_skill_tool_conformance.py` matches `COMMAND_HEADS` by prefix (`show` matched `sh`). Commit `0728ef5`. The checker was not changed.

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
- Task 2.3: `bash scripts/lint-doc-truth.sh` failed until Task 3.1 added `hooks/model-config.sh` to the CLAUDE.md hook table (now passes).
- Task 3.1: the synthetic-settings Codex exclusion test duplicates the real-`settings.json` render test.
- Task 3.1: the Codex exclusion matches the whole command basename, so a registration with arguments would leak; an event whose groups are all dropped would still emit `[]`.
- Task 4.1: `run_proof.py` does not pin the main-session model, so on a host whose default model is Sonnet a rerun could pass without the subagent frontmatter taking effect (the recorded run had an Opus main session, so it is valid).
- Task 4.1: `--prepare` reuses an existing proof directory without redeploying when `test-runner.md` contains `model: sonnet`, so a rerun after harness changes can test a stale deploy.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane evidence | `python3 .claude/scripts/verify_summary.py --lane model-effort-config` | 0 | intake-time check only | |
| snapshot render | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_render_agent_definitions.py -q -k defaults_out` | 0 | 5 passed | SC-1 |
| agent override | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_apply_model_config.py -q -k agent_override` | 0 | 2 passed | SC-2 |
| invalid input | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_apply_model_config.py -q -k invalid` | 0 | 34 passed | SC-3 |
| review floor | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_apply_model_config.py -q -k floor` | 0 | 3 passed | SC-4 |
| idempotent apply | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_apply_model_config.py -q -k idempotent` | 0 | 1 passed | SC-5 |
| show table | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_apply_model_config.py -q -k show` | 0 | 5 passed | SC-6 |
| main-session boundary | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_apply_model_config.py -q -k main_session_boundary` | 0 | 1 passed | SC-7 |
| skill line insert and remove | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_apply_model_config.py -q -k skill_line` | 0 | 2 passed | SC-8 |
| consumer skill untouched | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_apply_model_config.py -q -k consumer_skill` | 0 | 1 passed | SC-9 |
| partial write | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_apply_model_config.py -q -k partial_write` | 0 | 2 passed | SC-10 |
| hook contract | `bash tests/hooks/model-config.test.sh` | 0 | 12 passed, incl. one startup run under 1 s | SC-11 |
| hook root ratchet | `bash scripts/check-hook-root-source.sh` | 0 | no hook derives its root from its own location | SC-12 |
| deploy apply | `bash tests/scripts/model-config-deploy.test.sh` | 0 | 13 passed | SC-13 |
| deploy stops on invalid file | `bash tests/scripts/model-config-deploy.test.sh` | 0 | 13 passed, incl. re-sync, first deploy and dry-run cases | SC-14 |
| profile registration | `bash tests/scripts/deploy-profile.test.sh` | 0 | 26 passed | SC-15 |
| no PreModelSwitch hook | `python3 -c "import json,sys; sys.exit('PreModelSwitch' in json.load(open('settings.json'))['hooks'])"` | 0 | | SC-16 |
| Codex exclusion | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_render_codex_adapter.py -q` | 0 | 16 passed | SC-17 |
| manifest consistency | `python3 scripts/check_manifest.py` | 0 | manifest: consistent | SC-18 |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | hook table matches settings.json | SC-19 |
| skill mode table | `/tmp/harness-tests-venv/bin/python -m pytest scripts/test_harness_models_skill.py -q` | 0 | 3 passed | SC-20 |
| skill tool conformance | `python3 scripts/check_skill_tool_conformance.py` | 0 | 59 commands across 16 skills permitted | SC-21 |
| live proof prepare (consumer deploy) | `python3 specs/model-effort-config/proof/run_proof.py --prepare` | 0 | fresh git repo at `${TMPDIR:-/tmp}/harness-model-effort-proof`; harness-models.json sets test-runner to sonnet; deploy seconds 0.5; deployed test-runner.md has `model: sonnet` | SC-22 |
| live proof (headless test-runner dispatch) | `python3 specs/model-effort-config/proof/run_proof.py` | 0 | Claude Code 2.1.302; modelUsage keys claude-opus-5-5, claude-sonnet-5-5; claude -p seconds 9.1 (deploy excluded, prepared before) | SC-22 |

### Not auto-verified

- SC-22 makes one live, nondeterministic model call. It needs an authenticated `claude` and cannot run in CI. Tier: truth, for the `test-runner` role only (other roles and skill `effort` are not live-proven).

### Rollback

- `git revert <sha>` for each commit on `feat/model-effort-config` (filled with exact shas at ship).

### Harness-Delta

- backlog (Task 1.2): the worktree-isolation guard refuses compound shell commands (loops, `cd` then `git`), so implementers run each command alone.
- backlog (Task 3.1): `scripts/check_skill_tool_conformance.py` matches `COMMAND_HEADS` with `startswith`, so any backticked word that starts with a head (`show`, `github`, `lsof`) is read as a command and fails conformance. Match the first word instead.
