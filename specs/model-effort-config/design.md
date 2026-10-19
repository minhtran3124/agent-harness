# model-effort-config — Design

Written 2026-10-17. Pins: repo ecb77de; Claude Code docs read 2026-10-17 (sub-agents, skills, settings, hooks)

## Goal

Give harness users one optional, team-shared JSON file that sets the `model` and `effort` of each
subagent and skill. The harness applies it at install/deploy and at the start of a new session, and
never overrides a choice the user makes mid-session.

## Current state

- `agents/runtime-bindings.json` holds per-role `model`/`effort` for Claude and Codex. It is the
  source of truth for agent defaults.
- `scripts/render_agent_definitions.py` validates the bindings (`CLAUDE_EFFORTS`, closed lists)
  and writes `model`/`effort` into `.claude/agents/*.md` frontmatter. `scripts/deploy-harness.sh`
  calls it in `render_agents()`.
- `agents/*.json` and the renderer never deploy to consumers (`scripts/deploy-harness.sh`, comment
  above `CONSUMER_DATA`). A consumer cannot change model or effort without editing derived files.
- No `skills/*/SKILL.md` sets `model:` or `effort:`.
- `hooks/session-knowledge.sh` is the only SessionStart hook; it is registered without a matcher.
- A consumer's `.claude/` is gitignored and rebuilt by deploy, so a user file inside it is not
  durable.
- `docs/solutions/harness/review-model-diversity-dropped-decisions.md` (2026-10-02) records the
  choice of Opus 5.5 at `medium` for the review roles.

## Approaches considered

1. **Applier that rewrites deployed frontmatter (chosen).** One script reads the defaults snapshot
   and the user file, validates, and rewrites only the `model`/`effort` lines of deployed agent and
   skill files. Deploy, a SessionStart hook, and the `/harness-models` skill call it. It reuses the
   frontmatter Claude Code already reads, covers agents and skills, and never touches the main
   session. Cost: a new hook (high-blast), and agent changes may only apply from the next session.
2. **Dispatch-time injection.** Harness skills pass `model`/`effort` on every Agent call. It needs
   no hook, but it covers only harness-dispatched agents, cannot set a skill's effort, changes every
   dispatching skill, and applies file edits mid-session without any user action, against the
   agreed timing.
3. **Deploy-only, SessionStart re-runs deploy.** It reuses the pipeline, but a full `.claude/`
   rebuild at every startup is slow and can stop on protected-file conflicts.

## Architecture

| Component | Location | Role |
|---|---|---|
| Harness defaults | `agents/runtime-bindings.json` (unchanged) | `scripts/render_agent_definitions.py` gains `--defaults-out <file>`, which writes a resolved snapshot: `{"schema_version": 1, "agents": {<role>: {"model", "effort"?}}, "skills": {<name>: {"model"?, "effort"?}}}`. `agents` comes from the Claude roles. `skills` has one key per harness skill that deploy ships (each `skills/<name>/SKILL.md` outside `skills/_archive/`), holding the `model`/`effort` its source frontmatter declares; today every value is empty. Deploy places it at `.claude/harness-models.defaults.json`. |
| User file | `<repo>/harness-models.json` (optional, tracked) | `{"schema_version"?: 1, "agents"?: {<role>: {"model"?, "effort"?}}, "skills"?: {<name>: {"model"?, "effort"?}}}`. `schema_version` is optional and means `1` when absent; any other value is an error (`unsupported schema_version`). Values are strings; `null` is an error, so a default cannot be cleared from the file. |
| Applier | `scripts/apply_model_config.py`, added to `CONSUMER_SCRIPTS` | Modes `--show` (default), `--check`, `--apply`, `--hook`. Python standard library only. Interface below. |
| Hook | `hooks/model-config.sh`, SessionStart, matcher `startup\|clear` | Thin wrapper: pipes stdin to `apply_model_config.py --hook`. Registered in `settings.json` and in `harness-manifest.json` `hook_profiles` for `standard` and `strict`. |
| Skill | `skills/harness-models/SKILL.md` | Thin: maps `/harness-models [show\|check\|apply]` to the script mode and relays its output. |
| Docs | `CLAUDE.md` hook table, `skills/README.md`, `harness-manifest.json` (`skills` list gains `harness-models`; `hooks` and `hook_profiles` gain `model-config.sh`) | Kept in step so `scripts/lint-doc-truth.sh` passes. |

### Applier interface

```text
apply_model_config.py [--show | --check | --apply | --hook]
                      --project-root <dir>        # holds harness-models.json
                      [--claude-dir <dir>]        # default <project-root>/.claude; write target
                      [--defaults <file>]         # default <claude-dir>/harness-models.defaults.json
```

| Caller | `--project-root` | Other arguments |
|---|---|---|
| Hook (`hooks/model-config.sh`) | `$CLAUDE_PROJECT_DIR`, else `git rev-parse --show-toplevel` of the working directory, never the hook's own location (`docs/solutions/harness/hook-root-must-not-come-from-install-location.md`) | none |
| Skill (`/harness-models`) | `git rev-parse --show-toplevel` | none |
| Deploy, check step | the deploy target root | `--defaults <temp snapshot from source>` |
| Deploy, apply step | the deploy target root | `--claude-dir "$OUT"` |

The hook wrapper finds the applier as a sibling of its own code: `$HOOK_DIR/../scripts/apply_model_config.py`.
That resolves to `scripts/` in this repository (root `settings.json` runs bare `hooks/…`) and to
`.claude/scripts/` in a consumer. Only the applier's location comes from the hook's path; the
project root does not.

Targets are `<claude-dir>/agents/<role>.md` for each role in the snapshot's `agents`, and
`<claude-dir>/skills/<name>/SKILL.md` for each skill in the snapshot's `skills`. Every entry point
validates against the snapshot, so deploy (temp snapshot from source) and the hook and skill
(deployed snapshot) accept the same names. Consumer-owned agents and skills are never targets and
never valid user-file keys; their authors set `model`/`effort` in their own frontmatter. Files
without frontmatter (`agents/PROJECT.md`, `agents/PROJECT.template.md`) are never targets.

### Data flow

1. **Load.** Read the defaults snapshot. Read `harness-models.json` from the project root if it
   exists.
2. **Merge per field.** Effective value = the snapshot default, replaced by the user file's field
   when present. A skill absent from the user file takes its snapshot default, which today is no
   `model`/`effort`.
3. **Validate all targets before any write.**
   - Unknown top-level keys, and roles or skills absent from the snapshot, are errors.
   - `model` is one of `opus`, `sonnet`, `haiku`, `fable`, `inherit`, or matches `^claude-[a-z0-9.-]+$`.
     No model ID list is hardcoded, so a model upgrade needs no code change.
   - `effort` is one of `low`, `medium`, `high`, `xhigh`, `max`.
   - The review floor, `effort` ≥ `medium` for `reviewer` and `task-reviewer`, is a constant
     in the script. The JSON file cannot lower it.
4. **Write.** For each target, replace an existing `model:`/`effort:` frontmatter line where it
   stands. Insert a missing line after the last of `description:`, `tools:`, `model:` that is
   present, which matches the order `render_agent_definitions.py` writes. Delete a line whose
   value resolves to none. Every other byte is kept. A file whose content would not change is not
   written. Each write is atomic (temp file, rename).
5. **Hook mode.** Read the SessionStart JSON from stdin. A `source` other than `startup` or `clear`
   exits 0 with no output and no write. This repeats the hook matcher on purpose: the matcher can
   be edited in a consumer's settings, and the script must still never apply on `resume`,
   `compact` or `fork`. Keep both. Otherwise apply; return `reloadSkills` when a skill file
   changed, and one `additionalContext` line only when something changed or failed.
6. **Show mode.** Print one row per agent role and one per skill that has a non-empty effective
   value (from the snapshot or the user file): target, model, effort, source (`default` or
   `harness-models.json`). Warn when `CLAUDE_CODE_EFFORT_LEVEL`, `CLAUDE_CODE_SUBAGENT_MODEL` or
   `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` is set, because those override the configured values.

### Main-session boundary

The applier writes only the targets listed under "Applier interface". It never writes
`settings.json`, `settings.local.json`, or user settings, so `model`/`effortLevel` and the user's
`/model`/`/effort` choices stay the user's. No `PreModelSwitch` hook is registered.

### Deploy integration

Before it writes the derived tree, `deploy-harness.sh` renders the defaults snapshot from the
source `agents/runtime-bindings.json` and source `skills/` into a temp file. It then runs
`--check` with that snapshot, so the check sees the incoming roles and skills, not the old
`.claude/` copies, and works on a first deploy. On failure, deploy stops with the error and writes
nothing. The check runs before `preflight_protected`, so an invalid file stops deploy before any
protected-file conflict prompt, and a `--dry-run` reports the file's errors before it exits as it
does today. The apply step is a new pipeline step placed
immediately after `rewrite_derived_paths` and before `derive_settings`: it copies the snapshot to
`$OUT/harness-models.defaults.json` and runs the source `scripts/apply_model_config.py --apply
--claude-dir "$OUT"`. By that point `render_agents`, the skill copy and every Markdown rewrite are
done, so no later step changes the applied lines. The snapshot is top-level in `$OUT`, outside the
directories `prune_orphans` touches.

If the source tree has no `scripts/apply_model_config.py`, deploy warns and skips both steps, the
same way it treats any other missing allow-listed consumer script. A re-sync from a staged
`.harness-source/` is a known gap that predates this design: its `PAYLOAD` also lacks
`scripts/render_agent_definitions.py`, so `render_agents` fails first. This design does not fix
that path and makes no claim about it.

Docs: the `CLAUDE.md` hook table gains a row, and the "Hook profiles" paragraph changes "all three
hooks" to four.

## Error behavior

| Situation | `--check` / `--apply` / skill | Hook | Deploy / install |
|---|---|---|---|
| No user file | Defaults only | Defaults only, no output | Defaults only |
| Invalid JSON, unknown key/role/skill, bad value, below floor | Exit 1, one line per error, no file written. `--show` prints the same errors and exits 1. | Exit 0, no file written, `additionalContext` warns that the last applied values stay | Stops before writing, exit non-zero, prints the errors |
| A file write fails part-way (permission, disk) | Exit 1, names the files written and the file that failed | Exit 0, `additionalContext` says the apply was partial and names `/harness-models apply` | Exit non-zero, same report |
| Defaults snapshot missing or unreadable | Exit 1 | Exit 0, **no output** (a worktree session under `.claude/worktrees/<name>` has no deployed `.claude/`) | Check step: the temp snapshot failed to render, so deploy stops |
| Applier absent from the deployed tree | Not reachable | The wrapper finds no applier and exits 0 with no output | Source lacks it: warn, skip check and apply |
| `python3` missing | Not reachable (the skill runs python3) | Exit 0, no output | Not reachable (deploy needs python3) |

The hook never blocks a session. Validation is all-or-nothing; a write failure is not, but each
write is atomic and the applier is idempotent, so a re-run after the cause is fixed converges to the
full result.

## Tests

- `scripts/test_apply_model_config.py` (truth): merge, each validation error class, the floor,
  idempotence, a rewrite that keeps every non-target line, skill line insert and removal, the
  main-session boundary.
- `tests/hooks/model-config.test.sh` (truth, isolated temp git repo): `startup` and `clear` apply;
  `resume`, `compact`, `fork` leave every target file byte-identical; invalid file exits 0 with the
  warning and writes nothing; one `startup` run completes in under 1 s (budget).
- Deploy tests (`tests/scripts/deploy-prune.test.sh`, `tests/scripts/install-harness.test.sh`,
  `tests/scripts/consumer-subset.test.sh`): the consumer receives the applier and the snapshot, and
  `agents/*.json` still does not deploy; an invalid user file stops deploy with no write under
  `.claude/` (SC-10).
- `bash scripts/run-tests.sh`, including the doc-truth lint.
- xia2 probe for A1, A2, A3, A4, A5 and A6 (below), plus whether `model: inherit` is valid in
  `SKILL.md` frontmatter. All seven are go/no-go: a false result changes the design or what D9
  delivers, so it is a Rule 4 STOP that asks the user and is recorded as a `DC<n>`. For A4 or A5
  the question is whether a one-session lag after `startup`/`clear` is acceptable.

## Success criteria

- SC-1: With `{"agents": {"coding": {"effort": "high"}}}`, after deploy `.claude/agents/coding.md`
  frontmatter holds `effort: high`, and its diff against the default render is that one line.
- SC-2: Hook input `source` `startup` or `clear` applies the file; `resume`, `compact`, `fork`
  leave the sha256 of every target file unchanged.
- SC-3: An invalid file makes `--check` and `--apply` exit 1 with one line per error and leaves
  every target file's sha256 unchanged; the hook exits 0 and its output contains the warning.
- SC-4: `reviewer` or `task-reviewer` with `effort: low` is rejected by `--check` with exit 1.
- SC-5: A second `--apply` with unchanged inputs reports 0 files written.
- SC-6: `--show` prints one row per agent role and one per skill with a non-empty effective value,
  with a source column, and
  prints one warning line for each of `CLAUDE_CODE_EFFORT_LEVEL`, `CLAUDE_CODE_SUBAGENT_MODEL` and
  `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` that is set.
- SC-7: After `--apply` and the hook, `settings.json` and `settings.local.json` are
  byte-identical to before, and `settings.json` registers no `PreModelSwitch` hook.
- SC-8: A consumer deploy contains `.claude/scripts/apply_model_config.py` and
  `.claude/harness-models.defaults.json`, and contains no `agents/*.json`.
- SC-9: `bash scripts/run-tests.sh` exits 0.
- SC-10: With an invalid `harness-models.json` in the target, `deploy-harness.sh --target` exits
  non-zero, prints the applier's errors, and creates or changes no file under the target's
  `.claude/`.
- SC-11: With `{"skills": {"correctness-review": {"effort": "high"}}}`, `--apply` adds
  `effort: high` to `.claude/skills/correctness-review/SKILL.md` frontmatter. After that entry is
  removed from the file, the next `--apply` removes the line and the file is byte-identical to the
  default deploy.
- SC-12: A consumer skill `.claude/skills/my-skill/SKILL.md` (not in the snapshot) with
  `model: sonnet` keeps a byte-identical file after deploy, the hook and `--apply`; a user file
  naming `my-skill` is rejected by `--check` with exit 1.

## Non-goals

- Changing or reverting the main session's model or effort setting. A configured skill's
  `model`/`effort` applies to that skill's turn only (A2), which Claude Code defines; the session
  setting is never written.
- Tiers, named profiles, or a `.local` override layer.
- Codex runtime configuration (Codex keeps `runtime-bindings.json`).
- Choosing new default models for any role.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | Claude Code applies `model`/`effort` from `.claude/agents/*.md` frontmatter. | provenance: Docs, 2026-10-17, code.claude.com/docs/en/sub-agents.md (read by a research subagent) | xia2 probe (SC-1 checks only the file content) | Agent config has no effect; the design reduces to skills only. |
| A2 | Claude Code applies `model`/`effort` from `SKILL.md` frontmatter for the skill's turn. | provenance: Docs, 2026-10-17, code.claude.com/docs/en/skills.md (read by a research subagent) | xia2 probe | Skill entries have no effect; drop the `skills` map. |
| A3 | SessionStart input carries `source` (`startup`, `resume`, `clear`, `compact`, `fork`) and supports those matchers. | provenance: Docs, 2026-10-17, code.claude.com/docs/en/hooks.md | xia2 probe (Claude Code sends it); SC-2 (the script reads it) | The hook cannot tell a new session from a resume; it would apply on resume against D9. Fallback: no hook, deploy-only. |
| A4 | A SessionStart `reloadSkills` output reloads skill frontmatter in the same session. | none yet — Inference, 2026-10-17, code.claude.com/docs/en/hooks.md: the field is listed without semantics | xia2 probe (go/no-go) | A skill change made by the hook applies from the next session; Rule 4 STOP to ask whether that lag is acceptable. |
| A5 | An agent file rewritten by a SessionStart hook takes effect in the same session. | none yet | xia2 probe (go/no-go) | An agent change made by the hook applies from the next session; Rule 4 STOP to ask whether that lag is acceptable. |
| A6 | Agent frontmatter `effort`/`model` takes precedence over the session's `/effort`/`/model`. | provenance: Docs, 2026-10-17, code.claude.com/docs/en/sub-agents.md (read by a research subagent) | xia2 probe | A user's mid-session `/effort` reaches subagents; still consistent with D10, but `--show` must say so. |
| A7 | The hook finishes well inside the SessionStart timeout. | none yet — Inference, 2026-10-17, specs/model-effort-config/design.md Architecture: stdlib Python over fewer than 30 (prediction) small files, against a 1 s (budget) limit | tests/hooks/model-config.test.sh asserts one hook run completes in under 1 s (budget) | A slow hook delays startup; fallback is an mtime short-circuit. |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| A changed agent setting applies in the current session. | Agent reload after SessionStart is undocumented (A5). |
| The configured model is the model that runs. | `CLAUDE_CODE_SUBAGENT_MODEL_FORCE`, `CLAUDE_CODE_EFFORT_LEVEL`, managed `availableModels` and an Agent call's `model` parameter can override it; `--show` warns only for the env vars. |
| The configured model is available to the account. | The applier checks the name's shape, not account access. |
| A skill turn always runs on the user's `/model` choice. | A skill configured with `model`/`effort` runs its own turn on those values, then the session returns to the user's choice. |
| The configured effort is supported by the configured model. | The applier checks `effort` against one fixed list, not per model (for example `xhigh` or `max` on `haiku`). |
| The review floor guarantees review quality. | It bounds effort only; quality is measured by the review evals. |
| Codex follows the same file. | Codex is out of scope (D3). |
| A hand edit to a deployed agent or skill file survives. | The applier rewrites `model`/`effort` lines at the next new session (D8). |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | The user file is `harness-models.json` at the repository root, optional and tracked; there is one user file. | It survives re-sync and is shared by the team; no personal layer. | settled |
| D2 | The file is a flat map of `agents` and `skills`; no tiers or profiles in v1. | A model upgrade edits each entry that names it. | settled |
| D3 | Claude runtime only. | Codex keeps `runtime-bindings.json`. | settled |
| D4 | `reviewer` and `task-reviewer` effort below `medium` is rejected; the floor is a code constant. | A cost profile cannot silently weaken review. | settled |
| D5 | A skill absent from the file keeps its source default (none today); only harness skills are configurable, and consumer-owned agents and skills are never touched. | Current skill behavior is unchanged by default; consumer frontmatter is never rewritten. | settled |
| D6 | One skill, `/harness-models` (`show`, `check`, `apply`), backed by one script also used by deploy and the hook. | One code path for every entry point. | settled |
| D7 | Consumers get the feature: the applier and a resolved defaults snapshot deploy; `agents/*.json` still does not. | The deploy boundary gains two files. | settled |
| D8 | The applier rewrites only the `model`/`effort` frontmatter lines. | A hand edit of those lines in a deployed file is overwritten at the next new session. | settled |
| D9 | Apply automatically only at install/deploy and at SessionStart `startup` and `clear`; never on `resume`, `compact`, `fork`. The one mid-session exception is `/harness-models apply`, which the user runs and so is the user's own intent. | `startup` and `/clear` rewrite subagent and skill settings; they take effect in that session if A4/A5 hold, else from the next session (go/no-go in xia2). Nothing applies mid-session without a user action. | settled |
| D10 | Option A: the file governs subagents and skills; the main session's model/effort belong to the user; no settings writes and no `PreModelSwitch` hook. | A user's `/model` or `/effort` is never reverted. | settled |
| D11 | Approach 1: an applier that rewrites deployed frontmatter. | A new SessionStart hook (high-blast). | settled |
| D12 | Deploy runs `--check` against a snapshot rendered from source first, and stops on an invalid file before writing. | A typo blocks re-sync until fixed and never half-applies; only an I/O failure can leave a partial apply, which a re-run repairs. | settled |
| D13 | The hook is in the `standard` and `strict` profiles, not `minimal`. | Minimal consumers get the settings only at deploy. | settled |
