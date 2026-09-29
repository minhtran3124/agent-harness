# simplify-hook-surface — Design

Status: approach A approved by user 2026-09-29; spec review approved (3 rounds); awaiting user review of written spec
Lane: high-risk · Intake: `specs/simplify-hook-surface/SUMMARY.md`

## 1. Purpose

The harness registers too many hooks. Each Edit/Write runs four of them, and each one spawns its
own Python normalizer (~300 ms per edit, measured). A commit fans out to four sub-hooks, and every
one of them re-parses the payload and re-diffs the index. Half the hooks are nudges or conveniences
rather than gates. In consumer repos, several of them clash with what the repo already does:
`ruff format` overrides the repo's own formatter, and Python-only gates apply to non-Python repos.

The goal is a smaller, faster hook surface that keeps the important gates, with install profiles
so a repo that already has its own hooks can adopt only the core.

**Constraints**

- Keep these gates with their current semantics and assertions:
  - branch isolation, blocking by default;
  - secrets and `.env` scan;
  - pending-escalation deny;
  - lane evidence (`verify_summary.py --lane`);
  - run-state artifact gate;
  - risk corroboration, with index-safe modes (SC-8 invariant; `gate-modes.default.sh` 2-warn/7-block parity).
- Keep the existing settings merge in `scripts/deploy-harness.sh`. It already preserves consumer
  hooks and prunes harness hooks removed from source.
- The profile cannot live in `settings.json` `env`: re-sync drops it
  (`docs/solutions/harness/gate-mode-as-data-decisions.md`, Decision 2). Profile policy therefore
  lives in the manifest (data) and in the registered command line (`--profile <p>`).
- bash 3.2 compatible; no new runtime dependencies. The secrets scan must not require python3.

**Success criteria**

- SC-1: The root `settings.json` goes from 5 events / 6 matcher groups / 8 commands to 2 events /
  3 matcher groups / 3 commands (PreToolUse Bash, PreToolUse Write|Edit, SessionStart). No
  PostToolUse, UserPromptSubmit, or SessionEnd group remains.
- SC-2: A standard Claude Edit/Write payload is decided by `branch-isolation-guard.sh` without
  starting python3. Non-standard payloads (Codex `apply_patch`, unknown shapes) still go through
  the normalizer and still fail closed on a shared branch.
- SC-3: A non-git Bash call exits 0 with no subprocess beyond one `jq`. A `git commit` runs one
  hook process that computes the staged path list and the Lane once.
- SC-4: Under `strict`, every retained gate keeps its current block/warn/allow outcome for the same
  inputs. Under `standard`, it does too, except for the demotions listed in §2.5. Tests are ported,
  not dropped.
- SC-5: `--profile minimal|standard|strict` on install/deploy registers the hook set and checks in
  §3. The default is `standard`. Re-sync with no flag reuses the recorded profile.
- SC-6: The Codex adapter `hooks.json` regenerates from the new surface (standard set), and
  `scripts/run-tests.sh` passes, including doc-truth lint and the manifest checks.

## 2. Architecture

```
PreToolUse  Bash        → hooks/commit-gate.sh --profile <p>
PreToolUse  Write|Edit  → hooks/branch-isolation-guard.sh
SessionStart            → hooks/session-knowledge.sh          (standard, strict)
lib/: git-command.sh, lane.sh, gate-modes.default.sh, normalize-tool-input.py   (unchanged API)
```

### 2.1 `hooks/commit-gate.sh` (new; replaces 5 files)

It replaces `pre-bash-dispatch.sh`, `check-untracked-py.sh`, `commit-quality-gate.sh`,
`risk-corroboration.sh`, and `branch-guard.sh`.

**Flow**

1. **Parse.** Read the payload once, using the dispatcher's existing fast path: one `jq` for a
   Claude `Bash` payload whose command is a non-empty string. Anything else goes to the
   normalizer, and anything unclassifiable blocks with exit 2 (current dispatcher behavior).
2. **Filter.** Call `hook_cmd_is_git_commit_or_push`; if it does not match, exit 0. If the matcher
   lib is missing, exit 2.
3. **Profile.** Resolve the profile: the `--profile` argument, else `standard`. An unknown value
   becomes `standard` and a warning goes to stderr. Unknown values never loosen below standard.
4. **Push.** On `git push`, only `check_untracked_py` runs (strict), then the hook exits.
5. **Commit context.** On `git commit`, resolve the repo root exactly as today: `CLAUDE_PROJECT_DIR`,
   else git-from-CWD, never `SCRIPT_DIR`. An unresolvable root blocks. Compute once:
   `STAGED_PATHS`, `SPEC_SLUGS`, `LANE_VAL`, and the `VERIFY_SUMMARY` path.
6. **Run checks.** Run the check functions in a fixed order (table below). A check that blocks
   prints its message and the hook exits 2. The untracked-py deny keeps its stdout
   `permissionDecision:"deny"` JSON form and exit 0, which today's tests assert.

**Check functions**

Each check is a shell function that preserves today's code and messages; only duplicated
preambles are removed.

| Function | Source | Profiles |
|---|---|---|
| `check_untracked_py` | check-untracked-py.sh | strict |
| `check_secrets` | commit-quality-gate Check 1 | all |
| `check_escalations` | Check 1.5 | standard, strict |
| `check_lane_evidence` | Check 1.6 | standard, strict |
| `check_run_state` | Check 1.7 | standard, strict |
| `check_risk` | risk-corroboration.sh (incl. diff-size note) | standard, strict; strict implies `RISK_CORROBORATION_STRICT=1` |
| `check_plan_scope` | blast-radius-check.sh matching logic (`hook_lib_find_active_plan` + `<files>`/`**Files:**` parse), applied to staged paths | standard, strict — warn; blocks under `BLAST_RADIUS_STRICT=1` (knob kept) |
| `check_app_gates` | Checks 2 / 2.5 / 3 (debug, Verify re-run, pytest) | strict, or `REQUIRE_APP_GATES=1` in any profile |
| `check_not_auto_verified` | existing `REQUIRE_NOT_AUTO_VERIFIED` path | unchanged |

Existing env knobs keep their meaning in every profile:

- `RISK_WARN_CATEGORIES`
- `RISK_CORROBORATION_STRICT`
- `REQUIRE_APP_GATES`
- `REQUIRE_VERIFY`
- `REQUIRE_NOT_AUTO_VERIFIED`
- `REQUIRE_RUN_STATE_STAGED`
- `BLAST_RADIUS_STRICT`

Env knobs may tighten a lower profile. Only the knobs that already loosen today
(`RISK_WARN_CATEGORIES`, `REQUIRE_RUN_STATE_STAGED=0`) may loosen.

### 2.2 `hooks/branch-isolation-guard.sh` (modified)

The decision logic is unchanged: owner-checkout walk, specs-only exemption, and the break-glass
log. Only payload classification changes:

- **Fast path.** When `tool_name ∈ {Write, Edit}` and `.tool_input.file_path` is a non-empty,
  single-line string, `jq` alone yields `STATUS=known`, `TOOL_CLASS=edit`, and
  `PATHS=<repo-relative path>`. The path must be relativized against `ROOT` with the same rules
  the normalizer applies (`outside-root` → unknown, repository-root → unknown).
- **Fallback.** Any other shape (Codex `apply_patch`, `MultiEdit`, an array payload, a path with a
  newline) goes to the normalizer as today.

### 2.3 `hooks/session-knowledge.sh` (modified)

- Emit `critical-patterns.md` in full.
- Replace the full `INDEX.md` table with a single line: its path and entry count
  ("N entries — browse `docs/solutions/INDEX.md`").
- The run-state summary source is unchanged.
- It still never blocks.

### 2.4 Deleted

**Hooks**

- `ruff-on-edit.sh`
- `render-plan-on-write.sh`
- `scope-gate.sh`
- `state-breadcrumb.sh`
- `blast-radius-check.sh`
- `branch-guard.sh`
- the four merged commit hooks and `pre-bash-dispatch.sh`

**Their tests**

Assertions for retained behavior move into `tests/hooks/commit-gate.test.sh`.

**`hooks/lib/lane.sh`**

- Keeps `hook_lib_find_active_plan` and `hook_lib_resolve_lane`.
- Removes `hook_lib_intake_in_progress`, which only scope-gate used.

PLAN.html rendering remains available through the `visual-planner` skill.

### 2.5 Intentional behavior changes

The user approved these as part of approach A. They are listed so review does not read them as
regressions.

| Change | Before | After | Replacement / rationale |
|---|---|---|---|
| untracked `.py` deny | blocks commit/push in every repo | `strict` only | Python-specific. In non-Python consumers it is noise; in Python repos, `strict` restores it. `install-harness.sh`'s `.gitignore` line for `.claude/` stays, since it is harmless without the gate. |
| blast radius | PostToolUse warning on every edit (in-flight) | commit-time warning; still blocks with `BLAST_RADIUS_STRICT=1` | Per-edit cost (~100 ms) and stale-plan noise. The in-flight escalation trigger in `rules/orchestration.md` is re-worded: it is detected at each wave commit and by the task reviewer's spec verdict (the implementer reports `Files touched`), not per edit. |
| branch-guard warning on commit to main | stderr warning | retired | branch-isolation already denies non-`specs/` edits on a shared branch. A `specs/`-only commit on main is the sanctioned bookkeeping path. |
| `state-breadcrumb` Session End Log | appended to `specs/STATE.md` on every SessionEnd | retired | It dirtied a tracked file every session. Cross-session resume is `RUN.json` / `events.jsonl` via `subagent-driven-development resume <slug>`. The existing log content in `specs/STATE.md` stays as history; the templates stop mentioning auto-append. |
| `scope-gate` nudge | additionalContext on implementation-intent prompts | retired | CLAUDE.md and the `feature-intake` skill description already route. |
| `ruff-on-edit` | auto-format `.py` on edit | retired | It conflicted with consumer formatters. **Correction (2026-09-29, found in Task 6.2):** no ruff/lint step exists in `scripts/run-tests.sh` or `harness-ci.yml`, so after this change the repo has **no Python lint gate**; Python correctness rests on the pytest suites. Adding a CI lint step is a follow-up, not part of this change. |
| PLAN.html auto-render | on PLAN.md write | on demand via `visual-planner` | Convenience only. |

### 2.6 Codex adapter and capability evidence

- `scripts/render_codex_adapter.py` renders only the events that are present in `settings.json`.
  It still rejects unknown events. The "missing canonical {event} bindings" error applies only to
  PreToolUse, which remains required.
- `adapters/codex/plugin/hooks/hooks.json` is regenerated.
- Three capability-matrix rows (`specs/codex-support/capability-matrix.json`) are currently
  `load_bearing: true`, and the events they probe are no longer registered after SC-1:
  - `hooks.post_tool_use.shell`
  - `hooks.post_tool_use.apply_patch`
  - `hooks.session_end`

  These three become `load_bearing: false` and `support_target: "advisory"`, matching `hooks.user_prompt_submit`. `hooks.user_prompt_submit` is already false and is
  unchanged. `codex_harness_doctor.py` counts every load-bearing row, including `EVIDENCE_STALE`
  once `expires_at` passes, so evidence for an event the harness no longer uses must not hold the
  result at advisory.
- The SessionEnd probe in `scripts/capture_codex_capabilities.sh` and
  `tests/scripts/codex-capability-probe.test.sh` uses `state-breadcrumb.sh`. It switches to a
  self-contained fixture hook, like the PostToolUse probes already use; the probes are kept, only
  their load-bearing status changes.
- Invariant: the doctor must not drop to `unsupported` because an unregistered event is unprobed.

## 3. Profiles

`harness-manifest.json` gains a `hook_profiles` object. It is the authority, and
`check_manifest.py` validates it against the registered surface.

```json
"hook_profiles": {
  "default": "standard",
  "minimal":  { "hooks": ["branch-isolation-guard.sh", "commit-gate.sh"] },
  "standard": { "hooks": ["branch-isolation-guard.sh", "commit-gate.sh", "session-knowledge.sh"] },
  "strict":   { "hooks": ["branch-isolation-guard.sh", "commit-gate.sh", "session-knowledge.sh"] }
}
```

The per-check membership is the table in §2.1, which lives in `commit-gate.sh`. `profile_allows`
is a plain `case` statement, and `check_manifest.py` asserts the three profile names match.

**Selection and persistence**

1. `install-harness.sh` and `deploy-harness.sh` accept `--profile <p>`.
2. `derive_settings` filters the source `settings.json` hook entries to the profile's hook list and
   rewrites the commit-gate command to `… commit-gate.sh --profile <p>`.
3. The chosen profile is written to `.claude/.harness-profile`.
4. A re-sync without `--profile` reads that file (default `standard`).
5. An invalid `--profile` aborts the deploy before any write.

The source repo's own root `settings.json` registers the standard set. Its commit-gate command
has no `--profile` argument, so the runtime default is `standard`. `derive_settings` appends
`--profile <p>`; the merge prunes prior copies by the `.claude/hooks/` prefix, so a suffix change
cannot double-register. `.harness-profile` is written outside the synced-dir list and never
enters `.harness-deployed`, so `prune_orphans` cannot delete it.

`strict` re-enables the Python/`app/` gates (`check_app_gates`, untracked `.py`) for any repo that
selects it. That is the point of `strict`; non-Python repos should use `standard`.

**Trust note.** `.claude/.harness-profile` and the derived command line are agent-writable in a
consumer, the same trust tier as today's `settings.local.json` env knobs. The profile is an
adoption choice, not a security boundary. Durable policy (gate modes) still comes only from the
git index or the embedded defaults.

## 4. Error behavior

| Situation | Behavior |
|---|---|
| Unclassifiable Bash payload | block (exit 2), as today |
| Missing `git-command.sh` or `lane.sh` | block, as today |
| Missing `gate-modes.default.sh` | every category blocks, as today |
| python3 or `verify_summary.py` missing | lane evidence and Verify re-run fail open with a skip line, as today; the secrets scan does not need python3 |
| Unknown `--profile` at runtime | warn, run standard |
| Unknown `--profile` at deploy | abort, nothing written |
| Branch isolation, fast path cannot relativize the path | falls to the normalizer (never to allow) |

## 5. Tests

- `tests/hooks/commit-gate.test.sh` ports every case from:
  - `pre-bash-dispatch.test.sh`
  - `commit-quality-gate.test.sh`
  - `risk-corroboration.test.sh` (incl. SC-8 index-only reads)
  - `check-untracked-py.test.sh`
  - `warn-mode-smoke.test.sh`
  - `gate-integration.test.sh`
  - `command-matching.test.sh` (the matcher-only cases stay against `lib/git-command.sh`)

  It also adds per-profile cases: minimal skips the lane and risk checks; strict blocks an
  untracked `.py` and blocks a missing Lane.
- `branch-isolation-guard.test.sh` gains cases asserting that a Claude payload takes the fast
  path with no python3 (PATH without python3 still decides correctly) and that `apply_patch`
  still uses the normalizer.
- `tests/scripts/settings-merge.test.sh` is rewritten, because it asserts the counts for
  `ruff-on-edit` and `pre-bash-dispatch`. It covers:
  - profile filtering;
  - `.harness-profile` persistence;
  - `.harness-profile` surviving `prune_orphans` and `.harness-deployed`;
  - a commit-gate command suffix change deduping correctly;
  - a re-sync that prunes the removed hooks from a consumer settings file.
- These are retargeted from the removed files to `hooks/commit-gate.sh`:
  - `tests/scripts/workflow-engine-regex-parity.test.sh` (byte-parity with `check_review_receipt.py`)
  - `tests/scripts/consumer-subset.test.sh` (SC-8 `cmp`)
  - `scripts/check_gate_modes_smoke.py`
  - `scripts/check_manifest.py` Check B (`add_cat` set) and Check A (hooks inventory vs disk and settings)
  - `scripts/test_check_manifest.py`
  - `tests/hooks/normalize-tool-input.test.sh`
  - `tests/scripts/install-gitignore.test.sh` — asserts the `.gitignore` append only; its untracked-`.py` deny premise runs commit-gate under `--profile strict`. The comment at `scripts/install-harness.sh:237-240` is updated to match.
  - `scripts/test_render_codex_adapter.py`
  - `tests/scripts/codex-capability-probe.test.sh`
- `commit-gate.test.sh` includes a secrets-check case run with a PATH that has no python3, plus a `bash -n` syntax check.
- `repo-root-resolution.test.sh`, `spec-prefix-compat.test.sh`, and `codex-edit-hooks.test.sh`
  are retargeted to the surviving hooks.
- Tests for deleted hooks are removed.
- A latency check (informational, not CI-blocking) records per-event timing before and after in
  SUMMARY `### Verify`.

## 6. Manifest, prose, and documentation

The final grep gate is:

```
git grep -nE '<removed hook names>' -- ':!specs' ':!docs/research' ':!docs/harness-experimental' \
  ':!docs/harness-gap-closure-plan.md' ':!docs/harness-v03-plan-overview.md' ':!research-loop.md' \
  ':!evals' ':!CHANGELOG.md'
```

It must return nothing, except `docs/solutions/**` lines that carry the "superseded by
simplify-hook-surface" note.

**Code comments and docstrings** that name removed hooks:

- `hooks/lib/gate-modes.default.sh`
- `hooks/lib/lane.sh`
- `hooks/branch-isolation-guard.sh`
- `hooks/session-knowledge.sh`
- `scripts/ci-strict-gate.sh`
- `scripts/check_review_receipt.py:47`
- `scripts/verify_summary.py:357`
- `scripts/harness-audit.sh:7`
- `tests/lib.sh`

**`harness-manifest.json`**

- Update the `hooks` inventory.
- Add `hook_profiles`.
- Update the component `consumers` lists (`hook-input-normalization`, `hard-gate-vocabulary`,
  `artifact-schema-summary`, `hook-registration`).

**Rules** (these trip `workflow-engine`, so a **context-propagation audit is required**)

- `rules/orchestration.md`
- `rules/plan-format.md`
- `rules/auto-correct-scope.md`

**Skills and agents**

- `skills/README.md`
- `skills/correctness-review/correctness-scorer-prompt.md`
- `skills/compound/subagents/solution-extractor-prompt.md`
- `skills/feature-intake/tests/lane-classification-cases.md`
- `agents/PROJECT.md`

**Templates**

- `templates/SUMMARY.template.md`
- `templates/ESCALATIONS.template.md`
- `templates/structure/specs-STATE.md`
- `templates/structure/specs-README.md`

**Top-level docs**

- `CLAUDE.md`: the hook table plus the Gotchas that name removed hooks. Doc-truth lint enforces the table in the same PR.
- `CHANGELOG.md`: an entry noting the breaking change and `--profile`.

**Left as historical record**

These are dated records and are left unchanged:

- `docs/research/**`
- `docs/harness-experimental/**`
- `docs/harness-gap-closure-plan.md`
- `docs/harness-v03-plan-overview.md`
- `research-loop.md`
- `evals/**`

A `docs/solutions/**` entry that states current behavior gets a one-line "superseded by
simplify-hook-surface" note.

## 7. Out of scope

- Per-profile Codex adapters. Codex gets the standard set only.
- Cleaning up the three stale `status: active` plans (separate bookkeeping task).
- Changing any gate's detection regexes or modes.
- Pruning orphaned hook *files* left in a consumer's `.claude/hooks/`. Registration is pruned by
  the existing merge; file pruning follows existing deploy behavior.
