# simplify-hook-surface — Research Brief

Depth: **Deep** (intake lane high-risk → Deep; no upgrade needed, and depth cannot go lower).
External surface: none. No new dependency or integration. Claude Code hook semantics were checked
anyway, because they back the latency and compatibility claims.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Reuse existing: merge the existing hook bodies into `commit-gate.sh` as functions, and reuse the existing merge, prune, and renderer machinery with small targeted changes |
| **Why this is the lightest credible path** | Every retained check already exists with tests. The deploy merge already prunes removed harness hooks and orphaned files, and the doctor already treats evidence reasons as advisory, so no new mechanism is needed besides profile filtering |
| **Confidence** | 85% |
| **Next step** | `writing-plans`, which must add the 7 design corrections (D1–D7 below) as plan tasks |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Prompt and tooling framework (meta-repo, no application stack) |
| Primary language + runtime | bash 3.2-compatible shell hooks; Python 3 stdlib scripts |
| Frameworks / platforms | Claude Code hooks (settings.json); Codex CLI 0.147.0 adapter (alpha, advisory) |
| Relevant packages | `jq` (hard dependency of hooks), `python3` (normalizer, verify_summary, doctor) |
| Detectable versions | Codex evidence pinned `codex-0.147.0`, evidence expires 2026-11-08 |
| Important constraints | Hook root is `CLAUDE_PROJECT_DIR`, else git-from-CWD, never SCRIPT_DIR (`check-hook-root-source.sh` ratchet). Gate modes are read only from the index manifest or the embedded defaults (SC-8). `settings.json` `env` is dropped on re-sync |

## Feature Understanding and Assumptions

- **Requested feature:** Simplify the hook system: fewer, faster hooks that keep the important gates and stop conflicting with consumer repos that already have hooks.
- **What success appears to mean:** 3 registered hooks; standard edits never start python3; one process per commit; profiles for adoption; `run-tests.sh` green.
- **Assumptions from the request:** The design as approved (approach A, §2.5 demotions).
- **Assumptions still needing confirmation:** See the follow-up questions. There is one (MultiEdit), and it does not block.

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Docs` | Matching hooks run **in parallel**, and identical commands in one settings file are deduped (code.claude.com/docs/en/hooks.md). Per-edit wall time is therefore ≈ PreToolUse (113 ms) + the slowest PostToolUse (~100 ms) ≈ 215 ms, not the ~300 ms serial sum stated at intake. The saving is still real: after the change it is branch-isolation only, with no python3 |
| `Docs` | PreToolUse exit 2 blocks unconditionally. Exit 0 with JSON `permissionDecision:"deny"` denies. Other non-zero exits are non-blocking. Commands run through a shell, so arguments are allowed (hooks.md) |
| `Docs` | User, project, and managed settings hooks all merge and run (settings-reference.md). Consumer hooks co-exist; the conflicts are behavioral (ruff, Python-only gates), which confirms the design premise |
| `Docs` | `MultiEdit` is a valid tool name, and `Write\|Edit` is pipe-syntax exact matching, so the current branch-isolation matcher may not fire on MultiEdit. This is **pre-existing**, not introduced here |
| `Local` | `run-tests.sh:12,108` discovers suites by glob, so no registry edit is needed. `PYTESTS=` (:121) is an explicit list, but no hook pytest is in it |
| `Local` | `lint-doc-truth.sh:72-92`: a ✅ row must be in settings.json, any other row must not be, and `[ -f "$cmd" ]` runs on each **whole** settings command. The source `settings.json` must therefore keep commit-gate **without** `--profile`. Sections 1-2 and 4 flag any backticked path to a deleted file in docs, rules, skills, templates, and the derived tree |
| `Local` | `check_manifest.py` Check A (:41-60) inventory vs disk/settings; Check B (:135-149) hard-codes `hooks/risk-corroboration.sh` for `add_cat "slug"` literals; Check C (:152-175) requires every contract surface/consumer path to exist (`harness-manifest.json:72,177-182,189` name deleted hooks) |
| `Local` | `deploy-harness.sh`: argument parsing `:67-81`; `derive_settings` `:428-481` prunes old harness commands by the `$CLAUDE_PROJECT_DIR/.claude/hooks/` prefix (suffix-safe); `prune_orphans` `:515-526` already deletes previously deployed `hooks/*.sh` files that are no longer shipped. `.harness-profile` at the `.claude/` top level never matches `SYNCED_DIRS_RE` (:137), so it is not pruned |
| `Local` | `derive_settings` unions the event keys, so a consumer re-sync leaves `"PostToolUse": []`, `"UserPromptSubmit": []`, `"SessionEnd": []` |
| `Local` | `install-harness.sh` writes `.mcp.json` and backups (~:102, :172-208) **before** it calls deploy (:215-223), so `--profile` must be validated in the install argument parser, not only in deploy |
| `Local` | `render_codex_adapter.py:47-101` requires all 5 events; `validate_sources` (:153-158) requires the committed `hooks.json` to equal the rendered one (freshness). The doctor ignores `support_target` and only reads `load_bearing`. `unsupported` never comes from evidence (`codex_harness_doctor.py:337-390,433-473`) |
| `Local` | `specs/codex-support/neutralization-inventory.json` `scan_roots` lists `hooks/commit-quality-gate.sh`, `risk-corroboration.sh`, `scope-gate.sh` and their tests; `check_runtime_neutral_sources.py:194` errors on a missing scan root (it runs in `run-tests.sh:48`) |
| `Local` | `tests/lib.sh:56-59` `run_hook` cannot pass arguments to a hook |
| `Local` | `tests/scripts/settings-wiring.test.sh:26-38` requires derived commands to **exactly** equal `$CLAUDE_PROJECT_DIR/.claude/<root cmd>`. An appended `--profile` breaks it locally (the test is skipped in CI without `.claude/`) |
| `Local` | `render-plan-on-write.sh:37` runs `render_plan.py --summarize`, which refreshes the tracked AT-A-GLANCE block in `PLAN.md` (`rules/plan-format.md:184-194`). No skill passes `--summarize` today |
| `Local` | `session-knowledge.sh:72-80` already caps `critical-patterns.md` at 40 lines (headings only above that). The real file is 181 lines and 19.5 KB; the ~11.8 KB output today is mostly the 30 INDEX lines. The Codex SessionStart `additionalContextLimit` is 2500 |
| `Local` | `hook_lib_intake_in_progress` has one caller (`scope-gate.sh:39`). Nothing reads the `specs/STATE.md` Session End Log (`runtime/resume_decision.py:848-880` parses only `## Active Spec`) |
| `Inference` | Porting commit-gate test cases: about 41 (commit-quality-gate) + 38 (risk) + 8 (dispatch) + 7 (untracked-py) + 5 (warn-mode) + 4 (gate-integration) + about 10 (repo-root/spec-prefix subsets) ≈ 110 cases. This is the dominant cost of the plan |

## Local Findings

- **Relevant files:** as design §2, §5, §6, plus the ones the design missed (D1–D7):
  - `specs/codex-support/neutralization-inventory.json`
  - `tests/scripts/settings-wiring.test.sh`
  - `tests/scripts/codex-alpha-contract.test.sh` (calls `settings-wiring`, `test_render_codex_adapter`)
  - `README.md:67`
  - `docs/solutions/critical-patterns.md:124`
  - `docs/solutions/INDEX.md` (generated; a filename contains `risk-corroboration`)
  - `skills/writing-plans/SKILL.md:31-32`
  - `skills/visual-planner/SKILL.md`
- **Extension points:**
  - `derive_settings`'s first `jq` (profile filter plus `--profile` append).
  - The deploy/install argument parsers.
  - `expected_codex_hooks` (make absent events optional).
  - `tests/lib.sh` (add an args-capable runner).
- **Conventions to preserve:**
  - bash 3.2 (no `declare -A`, `mapfile`, `grep -P`).
  - The fail-closed messages `… redeploy harness (blocking to fail safe)`.
  - Blocking messages go to stderr; the untracked-py deny is stdout JSON with exit 0.
  - The literal strings asserted by parity tests must remain byte-identical in `commit-gate.sh`:
    - the `add_cat "slug"` literals
    - `git show :harness-manifest.json`
    - the workflow-engine `INCLUDE`/`EXCLUDE` regexes
- **Reusable:** all check bodies (verbatim); `lib/git-command.sh`; `lib/lane.sh` (minus one helper); `lib/gate-modes.default.sh`; the normalizer; the merge, prune, and renderer freshness machinery.
- **Missing locally:** profile filtering; the `.harness-profile` read/write; an args-capable test runner; an explicit `--summarize` caller.

## Upstream Findings

- **Repositories inspected:** none. This is local-only tooling with no comparable upstream implementation searched. Claude Code hook semantics were checked through the official docs (below).
- **Pattern upstream:** Claude Code runs matching hooks in parallel and dedupes identical commands, so hook count matters less than per-hook cost and behavior. This supports a design that targets python3 spawns and behavioral conflicts, not only the count.
- **Gaps:** runtime handling of empty event arrays (`"PostToolUse": []`) was not verified. The plan should prune them anyway (D5).

## Docs Findings

- **Official sources checked:** code.claude.com/docs/en/hooks.md, code.claude.com/docs/en/settings-reference.md, through a docs-lookup subagent.
- **Version status:** current docs; the harness does not pin a Claude Code version.
- **Built-in capabilities:** parallel execution, per-hook `timeout`, `statusMessage`, shell-form arguments, exec-form `args` array.
- **Caveats:** exit codes other than 0 and 2 are non-blocking, so commit-gate must block only with exit 2 or deny JSON, never exit 1. Top-level unknown settings keys are stripped (another reason not to store the profile in settings).

## Design corrections for writing-plans (D1–D7)

| # | Correction | Why |
|---|---|---|
| D1 | `session-knowledge.sh` keeps the **existing** 40-line cap on `critical-patterns.md` (headings only above it). Replace only the 30-line INDEX head with a pointer line. Update the test cases (:65-77, :102-107, :183-191, :217-222 expect entry text) | The design's "emit in full" would grow the output to ~20 KB, the opposite of the goal. This is an unapproved behavior change caught by research |
| D2 | Add `specs/codex-support/neutralization-inventory.json` `scan_roots` → `hooks/commit-gate.sh`, `tests/hooks/commit-gate.test.sh` | `check_runtime_neutral_sources.py` errors on a missing scan root |
| D3 | `tests/lib.sh`: add `run_hook_args <repo> <hook> <json> -- <args…> [VAR=val…]` (or similar). Fix the stale header comments | `run_hook` cannot pass `--profile` |
| D4 | `settings-wiring.test.sh` compares derived commands after stripping one trailing ` --profile <p>` from commit-gate. Root `settings.json` keeps a bare commit-gate command | The lint `[ -f "$cmd" ]` and the exact-match wiring test would otherwise conflict |
| D5 | `derive_settings` drops event keys whose array ends up empty after the merge | Otherwise re-synced consumers keep `"PostToolUse": []` and similar |
| D6 | `install-harness.sh` validates `--profile` in its own argument parser before any write, and forwards it to deploy | Install writes `.mcp.json` before it calls deploy |
| D7 | The AT-A-GLANCE refresh moves from the hook to the skills: `writing-plans` (after writing PLAN.md) and `subagent-driven-development` (at each wave-boundary Status Log update) run `render_plan.py <PLAN> --summarize`; `visual-planner` documents `--summarize`. Update `rules/plan-format.md:184-194` | The design's "PLAN.html is convenience only" missed that the hook also keeps a **tracked** block in PLAN.md current |

Also confirmed: install-gitignore.test.sh never runs a hook, so only its comments and title change.
This supersedes the design §5 note about running it "under --profile strict".

## Recommendation

- **Primary recommendation:** reuse existing, as in the Bottom Line.
- **Why lightest:**
  - Each piece of new logic is at most a few dozen lines: the profile `case`, the jq filter, and the `.harness-profile` read/write.
  - Everything else is a move or a retarget, and the existing machinery covers pruning and orphans (`deploy-harness.sh:457,515`).
- **Why the next-best alternative lost:**
  - Keeping the sub-hooks behind a shared-context dispatcher (approach B) keeps 4 processes and 4 files for the same test churn.
  - A Python rewrite (C) makes the secrets gate depend on python3.
- **What would change this:** if the ~110 ported test cases prove too costly for one PR, split into two PRs:
  1. commit-gate merge and deletions;
  2. profiles and Codex.

  Wave boundaries in the plan should make that split possible.

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - **(a) Test-port fidelity.** A case dropped during the port silently weakens a gate. Mitigation: a per-source case-count ledger in SUMMARY (old count → ported count, with retired cases named).
  - **(b) Literal-string parity.** The parity tests need the literals byte-exact in `commit-gate.sh`.
  - **(c) The PostToolUse/SessionEnd probe rewrite** in `capture_codex_capabilities.sh` changes the canonical `CONFIG_HASH` string only if SessionEnd config text changes. Keep the hash input unchanged, or update the matrix `config.sha256` (the KNOWN GAP comment at :174-183).
  - **(d) A local `.claude/` re-deploy** must not happen during the work (memory: never mutate `.claude/` without confirmation). Tests that read `.claude/` stay skipped or keep the old wiring until the user re-deploys.
- **Evidence gaps:**
  - The empty-event-array runtime behavior is unverified (mitigated by D5).
  - The MultiEdit matcher behavior was not reproduced.
- **Version uncertainties:** Codex evidence expires 2026-11-08, which is unrelated to this change.
- **Follow-up questions for the user (non-blocking):** should `MultiEdit` be added to the branch-isolation matcher (`Write|Edit|MultiEdit`) in this change? It is a pre-existing possible bypass of a gate we keep. The default is **no**: out of scope, record it as a backlog item.

## Source Pack

- **Local files read:**
  - `hooks/*.sh`, `hooks/lib/*`
  - `settings.json`, `harness-manifest.json`
  - `scripts/deploy-harness.sh`, `scripts/install-harness.sh`, `scripts/run-tests.sh`, `scripts/lint-doc-truth.sh`
  - `scripts/check_manifest.py`, `scripts/test_check_manifest.py`, `scripts/check_gate_modes_smoke.py`, `scripts/check_slim_surface.py`
  - `scripts/render_codex_adapter.py`, `scripts/test_render_codex_adapter.py`
  - `scripts/codex_harness_doctor.py`, `scripts/check_codex_capabilities.py`, `scripts/capture_codex_capabilities.sh`
  - `scripts/check_review_receipt.py`, `scripts/ci-strict-gate.sh`, `scripts/verify_summary.py`, `scripts/harness-audit.sh`, `scripts/harness-status.sh`
  - `tests/lib.sh`, `tests/hooks/*.test.sh`
  - `tests/scripts/{settings-merge,settings-wiring,consumer-subset,install-gitignore,workflow-engine-regex-parity,codex-capability-probe,codex-alpha-contract}.test.sh`
  - `specs/codex-support/capability-matrix.json`, `specs/codex-support/neutralization-inventory.json`
  - `adapters/codex/plugin/hooks/hooks.json`
  - `docs/solutions/harness/gate-mode-as-data-decisions.md`, `docs/solutions/INDEX.md`
  - `rules/plan-format.md`, `rules/auto-correct-scope.md`, `rules/orchestration.md`
  - `skills/visual-planner/SKILL.md`, `skills/writing-plans/SKILL.md`
  - `runtime/resume_decision.py`, `.github/workflows/harness-ci.yml`
- **Upstream repositories or pages checked:** none found (no comparable upstream hook-consolidation implementation was searched; the relevant upstream is the Claude Code runtime, covered under docs)
- **Official docs domains or pages checked:** https://code.claude.com/docs/en/hooks.md, https://code.claude.com/docs/en/settings-reference.md

## Evidence Boundary

> Confirmed from artifacts: every `Local` row above (file:line cited; spot-checked directly:
> session-knowledge 40-line cap, neutralization-inventory scan_roots, settings-wiring exact match,
> plan-format `--summarize` dependency, render_codex_adapter required events, capability-matrix
> load_bearing values).
> Inferred from patterns: test-port case total (~110); per-edit wall-time after change.
> Not checked: runtime acceptance of empty hook event arrays; MultiEdit matcher behavior in a live
> session; Codex runtime behavior after regeneration (needs `codex_harness_doctor.py` on a real
> install, outside hooks).
