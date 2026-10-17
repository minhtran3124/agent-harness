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
- Fix round on Task 1.2 (`6ff9bc5`): SC-6 and design say "a source column"; `--show` now prints per-field `model-source` and `effort-source` columns (intent-review finding #1). SC-6's minimum still holds.
- Fix round on Task 1.2 (`6ff9bc5`): no test sets both fields in one entry, or a field equal to its default.
- Fix round on Task 1.2 (`6ff9bc5`): the `load()` return annotation at `scripts/apply_model_config.py:134` still says `bool` for the third element, which is now a `frozenset`. Correctness re-review of `79643b6..6ff9bc5` (enclosing-function, every `merge()` caller traced) found no defect.
- Task 4.1: `--prepare` reuses an existing proof directory without redeploying when `test-runner.md` contains `model: sonnet`, so a rerun after harness changes can test a stale deploy.

### Correctness Review

Range `34b0b10..84ebbfe`. Six FIND angles: enclosing-function, removed-behavior, call-site-impact, stack-defects,
guard-completeness, prior-art (prior-art: 0 findings). Seven deduplicated locations, each scored once in a fresh
context. Threshold 75 (`review-config.json`). No finding reached the threshold, so no fix round ran.

### Advisory Findings

| Location | Finding | Score |
| --- | --- | --- |
| `scripts/apply_model_config.py:20` | `MODEL_ID` with `$` and `.match` accepts a trailing newline (`"claude-x\n"`); `rewrite` then adds one blank frontmatter line per apply. Fix: `fullmatch` or `\Z`. | 50 |
| `scripts/apply_model_config.py:172-175` | With duplicate `model:`/`effort:` keys, set rewrites only the first copy while delete removes all; a last-key-wins loader keeps the stale value. | 50 |
| `scripts/apply_model_config.py:181` | An inserted line ends in `\n` in a CRLF file (replace keeps the file's ending). | 50 |
| `scripts/deploy-harness.sh:538-541` | If `--apply` exits 1 after the check passed (write error), `set -e` aborts deploy before `derive_settings`, `.harness-profile`, `prune_orphans` and `.harness-deployed`; temp files leak. | 50 |
| `skills/harness-models/SKILL.md:15-24` | The skill takes the root from `git rev-parse --show-toplevel`; the hook prefers `CLAUDE_PROJECT_DIR`. In a session rooted at the main checkout with its working directory in a deployed linked worktree, `apply` edits the worktree's `.claude/`. | 50 |
| `harness-manifest.json:238` | `harness-models` ships into the Codex plugin, where the applier and snapshot do not exist, so the skill fails there (accepted under D3; PLAN Risks). | 50 |
| `scripts/render_codex_adapter.py:102` | An event whose only groups contain `model-config.sh` would render as `[]`; not reachable with today's `settings.json`. | 25 |

### Intent Findings

Intent review (plan-blind) over `34b0b10..84ebbfe`: every SC-1…SC-22 has a passing `Criterion` row.

- Fixed — drift: `--show` gave one source per row, so a default `model` read `harness-models.json` when only `effort` was set ("where each value came from"). Now per field. Commit `6ff9bc5`.
- Decided (E001, option A, 2026-10-17) — drift: only harness agents and skills are configurable; consumer-owned ones are rejected and never rewritten ("each agent and skill"). Kept as built (design D5); a later spec can widen it.
- Advisory — drift: the user file is a separate root `harness-models.json` overlay, not an extension of `agents/runtime-bindings.json`; defaults still come from the bindings. Same outcome, different form.
- Report only — excess: `--show` warns when `CLAUDE_CODE_EFFORT_LEVEL`, `CLAUDE_CODE_SUBAGENT_MODEL` or `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is set.

### Context-Propagation Audit

Result: **PASS** (no failed rows). Base `34b0b10`, head `0728437`. Consumer search surface:
`grep -rln -e harness-models -e apply_model_config -e model-config.sh skills agents rules CLAUDE.md HARNESS.md AGENTS.md`
found only `skills/harness-models/SKILL.md`, `skills/README.md` and `CLAUDE.md`. No dispatch prompt, agent or rule
relies on the new skill, applier or hook. The diff changes no `agents/*.md` and no `rules/*.md`.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `skills/harness-models/SKILL.md` (modes, literal `--project-root`, D9 "apply is the user's action", next-session note) | `/harness-models` invocation | main session | skill body loaded on invocation; deploy rewrites `scripts/` to `.claude/scripts/` | inspected `.claude/skills/harness-models/SKILL.md` lines 4, 23–25 name `.claude/scripts/apply_model_config.py`; `check_skill_tool_conformance.py` exit 0 (SC-21); `test_harness_models_skill.py` (SC-20) |
| applier `--apply` report (skill vs agent timing, A5) | user via `/harness-models apply` | main session | script stdout relayed verbatim by the skill (step 5) | `test_apply_model_config.py` report tests; SKILL.md step 5 |
| `harness-models.json` values → agent frontmatter `model`/`effort` | each dispatched subagent | fresh child context | Claude Code reads `.claude/agents/<role>.md` frontmatter at session start | SC-22 live proof: deployed `test-runner` ran on `claude-sonnet-5-5` in a new headless session (truth, one role); research-brief probe 1 (A1, A6) |
| `harness-models.json` values → skill frontmatter `model`/`effort` | skill turn | main session (skill turn) | Claude Code reads `SKILL.md` frontmatter at invocation | research-brief probes 3 and 4 (A2, A4, truth); `skill_line` tests (SC-8) |
| SessionStart re-apply (`startup`, `clear` only) | next session's subagents and skills | new session | `settings.json` SessionStart matcher `startup\|clear` → `hooks/model-config.sh` → `--hook` (repeats the source filter) | `tests/hooks/model-config.test.sh` (SC-11); `deploy-profile.test.sh` (SC-15); deployed `.claude/settings.json` registers `model-config.sh` (1 match); A5: agents apply from the next session in headless runs (accepted, Intake notes) |
| `CLAUDE.md` hook-table row and "all four" profile wording | every session | main and subagent contexts (CLAUDE.md is always loaded) | always-loaded | `lint-doc-truth.sh` exit 0 (SC-19); `check_manifest.py` exit 0 (SC-18) |
| `skills/README.md` inventory row | maintainers and agents reading the inventory | main session | explicit Read when consulted | `lint-doc-truth.sh` exit 0 (paths exist in source and consumer) |

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
