---
slug: hook-surface-slim
status: shipped
owner: minhtran3124
created: 2026-08-06
---

# hook-surface-slim — Package A+B implementation

## 1. Motivation

Reduce always-on hook process tax (Package A) and stop consumer repos from fail-closing every
risk category when `harness-manifest.json` is missing at repo root (Package B). Human approved
defaults in `design.md` §9 / `design-ab.md` §8: A1-thin, A2e, A3-delete, A4-detect `app/`,
B-hybrid, sequence A→B. Package E (simplify/task-review ceremony) is out of scope.

## 2. Non-goals

- Do not remove `branch-guard.sh` or `branch-isolation-guard.sh`.
- Do not loosen the seven block-mode risk categories (`auth`, `authorization`, `data-loss/migration`,
  `audit/security`, `external-provider`, `public-contract`, `high-blast`).
- Do not implement A1-lib (function-body merge) or A2a active-plan marker files.
- Do not ship a lite settings profile or change Superpowers-6 / simplify-stage skills.
- Do not require consumers to commit a root `harness-manifest.json`.

## Global Constraints

- Security block semantics for auth/authorization/data-loss/audit/external-provider/public-contract/high-blast stay fail-closed; only restore meta-repo warn parity for the two already-warn slugs plus identical defaults when manifest is absent.
- PreToolUse Bash non-commit path must run exactly one harness command process (the dispatcher); sub-checks may run only on matched git commit/push.
- Individual hook scripts remain directly executable for contract tests and manual debug (thin wrappers or unchanged bodies).
- Deployed mode artifacts under `.claude/` are harness-owned derived data; root tracked manifest (when present) always wins mode resolution.
- Generated default gate modes must be CI-pinned to `harness-manifest.json` detectable modes (no silent drift).
- Same-wave tasks must not edit overlapping files; waves are A then B.
- No whole-suite command as a task Verify or SC check row (use focused hook/script tests under 60s).
- Do not weaken Check 1 secrets, Check 1.5 escalations, or Check 1.6 lane evidence.

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
|---|---|---|---|
| SC-1 | `settings.json` registers a single Bash PreToolUse dispatcher; the four former Bash hooks are not separately registered | `python3 scripts/check_manifest.py` | exit 0 |
| SC-2 | Non-commit Bash through the dispatcher exits 0 without running commit-only bodies; commit/push still enforce untracked-py, quality, risk, and branch-guard in order | `bash tests/hooks/pre-bash-dispatch.test.sh` | exit 0 |
| SC-3 | Active-plan lookup short-circuits without full `ls -t` cost semantics change: zero active plans → blast silent; active plan still scopes files | `bash tests/hooks/blast-radius-check.test.sh` | exit 0 |
| SC-4 | Dormant `auto-test-on-change.sh` is gone from disk, manifest, and docs inventory | `python3 scripts/check_manifest.py` | exit 0 |
| SC-5 | commit-quality Checks 2/2.5/3 run only when repo-root `app/` exists; secrets/escalations/lane evidence unchanged | `bash tests/hooks/commit-quality-gate.test.sh` | exit 0 |
| SC-6 | Without root manifest, risk modes match meta-repo warn/block set via `.claude` manifest and/or generated defaults; auth + Lane normal still blocks | `bash tests/hooks/warn-mode-smoke.test.sh` | exit 0 |
| SC-7 | Deploy/install places mode manifest under `.claude/` for consumers | `bash tests/scripts/deploy-manifest-modes.test.sh` | exit 0 |
| SC-8 | Doc-truth and gate-mode smoke stay consistent with wiring | `bash scripts/lint-doc-truth.sh` | exit 0 |

## 4. Tasks

### Task 1.1 — Dispatcher contract tests first (wave 1)


- **Files:** tests/hooks/pre-bash-dispatch.test.sh
- **Criteria:** SC-2
- **Interfaces:** Consumes existing hook-test harness patterns and the four current Bash hook behaviors as oracles; produces `tests/hooks/pre-bash-dispatch.test.sh`.
- **Action:** Write contract tests targeting `hooks/pre-bash-dispatch.sh`: (1) non-commit command exits 0 silent; (2) `git commit` with untracked `.py` denies like check-untracked-py; (3) missing lib fails closed on blocking path; (4) commit path invokes quality/risk/branch-guard semantics. Use `new_repo` + `run_hook` patterns from sibling hook tests. Tests may fail until Task 1.2 adds the dispatcher.
- **Verify:** `test -f tests/hooks/pre-bash-dispatch.test.sh`
- **Done:** Test file exists with the four cases above encoded.

### Task 1.2 — Thin Bash PreToolUse dispatcher + settings wiring (wave 2)

- **Files:** hooks/pre-bash-dispatch.sh, settings.json, harness-manifest.json
- **Criteria:** SC-1, SC-2
- **Interfaces:** Consumes `tests/hooks/pre-bash-dispatch.test.sh` and the four existing Bash hook scripts; produces `hooks/pre-bash-dispatch.sh` plus updated `settings.json` and `harness-manifest.json` with a single Bash PreToolUse command.
- **Action:** Implement thin dispatcher: parse command once, source `lib/git-command.sh`, exit 0 unless commit/push; on push run only check-untracked-py; on commit run untracked → commit-quality → risk → branch-guard in order, stop on exit 2, forward stdout/stderr. Keep the four scripts as direct entrypoints. Update `settings.json` Bash matcher to only `hooks/pre-bash-dispatch.sh`. Manifest: add dispatcher `wired: true`; set the four former Bash hooks `wired: false` (still on disk). Do not change Write/Edit or other events.
- **Verify:** `bash tests/hooks/pre-bash-dispatch.test.sh`
- **Done:** SC-1/SC-2 green; existing per-hook tests still callable on the four scripts.

### Task 1.3 — Preserve gate-integration + per-hook suites after dispatch (wave 3)

- **Files:** tests/hooks/gate-integration.test.sh, tests/hooks/command-matching.test.sh
- **Criteria:** SC-2
- **Interfaces:** Consumes `hooks/pre-bash-dispatch.sh` and individual Bash hooks; produces updated `tests/hooks/gate-integration.test.sh` and `tests/hooks/command-matching.test.sh` if registration assumptions changed.
- **Action:** Adjust only what breaks due to settings/manifest wiring. Re-run untracked, commit-quality, risk, branch-guard unit suites unchanged in behavior. Ensure gate-integration still proves matcher end-to-end (via branch-guard and/or dispatcher).
- **Verify:** `bash tests/hooks/gate-integration.test.sh`
- **Done:** Integration and command-matching green with dispatcher live.

### Task 2.1 — A2e fast active-plan lookup (wave 4)

- **Files:** hooks/lib/lane.sh, tests/hooks/blast-radius-check.test.sh
- **Criteria:** SC-3
- **Interfaces:** Consumes `specs/*/PLAN.md` status lines; produces faster `hook_lib_find_active_plan` without changing active-only semantics.
- **Action:** Replace full `ls -t` + per-file grep scan with a short-circuit search that stops at the first `status: active` PLAN (no mtime fallback to shipped plans). Prefer a single-pass approach that avoids sorting the entire specs tree when zero or one active plan exists. Keep bash 3.2 portability. Extend blast-radius tests if needed for multi-active edge (document first-match). Behavior with zero active plans remains silent exit 0.
- **Verify:** `bash tests/hooks/blast-radius-check.test.sh`
- **Done:** Existing blast cases pass; lookup no longer depends on sorting every PLAN.md by mtime for the common zero-active case.

### Task 2.2 — Delete dormant auto-test-on-change (wave 4)

- **Files:** hooks/auto-test-on-change.sh, tests/hooks/auto-test-on-change.test.sh, harness-manifest.json, CLAUDE.md
- **Criteria:** SC-4
- **Interfaces:** Consumes dormant auto-test inventory entries; produces updated `harness-manifest.json` and `CLAUDE.md` with auto-test removed (hook and test files deleted).
- **Action:** Delete the dormant hook and its test. Remove manifest hooks entry. Strip live inventory rows/references outside historical `docs/` and `specs/` archives. Run manifest check. Do not wire a replacement.
- **Verify:** `python3 scripts/check_manifest.py`
- **Done:** No disk hook, no wired/false inventory row, `check_manifest.py` exit 0.

### Task 3.1 — A4 detect app/ before Checks 2–3 (wave 5)

- **Files:** hooks/commit-quality-gate.sh, tests/hooks/commit-quality-gate.test.sh
- **Criteria:** SC-5
- **Interfaces:** Consumes staged diff and repo layout; produces app-gated Checks 2/2.5/3 only when `app/` directory exists at repo root.
- **Action:** After Check 1.6, if `[ ! -d app ]` skip Checks 2, 2.5, and 3 with a clear stderr skip line (still exit 0). When `app/` exists, preserve current behavior including REQUIRE_VERIFY. Add tests: harness-like repo without `app/` does not run pytest mapping; repo with `app/` still blocks breakpoint. Secrets/escalations/lane evidence tests remain green.
- **Verify:** `bash tests/hooks/commit-quality-gate.test.sh`
- **Done:** SC-5 satisfied; Check 1.x unchanged.

### Task 4.1 — Generate default gate modes + resolve chain (wave 6)

- **Files:** hooks/risk-corroboration.sh, hooks/lib/gate-modes-default.sh, scripts/generate_gate_modes_default.py, scripts/check_gate_modes_smoke.py, tests/hooks/risk-corroboration.test.sh, tests/hooks/warn-mode-smoke.test.sh
- **Criteria:** SC-6
- **Interfaces:** Consumes `harness-manifest.json` hard_gates.detectable; produces `gate-modes-default.sh` and risk-corroboration resolve order: index root manifest, then `.claude/harness-manifest.json`, then defaults.
- **Action:** Add a small generator (or checked-in generated file updated by smoke/CI) exporting the slug=mode map matching the manifest. Change `GATE_MODES` load order per design B-hybrid. Extend warn-mode-smoke and risk tests: temp repo with no root manifest but `.claude/harness-manifest.json` warn pair; temp repo with neither uses defaults and still blocks auth under-classification; meta-repo index path unchanged. Keep RISK_WARN_CATEGORIES override.
- **Verify:** `bash tests/hooks/warn-mode-smoke.test.sh`
- **Done:** SC-6 green; `check_gate_modes_smoke.py` pins default file ↔ manifest.

### Task 5.1 — Deploy/install copy manifest into .claude (wave 7)

- **Files:** scripts/deploy-harness.sh, scripts/install-harness.sh, tests/scripts/deploy-manifest-modes.test.sh
- **Criteria:** SC-7
- **Interfaces:** Consumes source `harness-manifest.json`; produces `.claude/harness-manifest.json` on deploy/install targets.
- **Action:** After hooks sync (or in derive step), copy source manifest into `$OUT/harness-manifest.json` under the deploy output `.claude/`. Ensure install path gets the same artifact. Add a focused shell test that runs deploy into a temp dir and asserts the file exists and jq-parses detectable modes. Do not force-add root consumer manifest. Document in install help/ok message if appropriate.
- **Verify:** `bash tests/scripts/deploy-manifest-modes.test.sh`
- **Done:** Fresh deploy target has `.claude/harness-manifest.json` with warn modes for workflow-engine and weakening-validation.

### Task 6.1 — Docs truth + SUMMARY evidence closeout (wave 8)

- **Files:** CLAUDE.md, HARNESS.md, specs/hook-surface-slim/SUMMARY.md, specs/hook-surface-slim/PLAN.md
- **Criteria:** SC-8
- **Interfaces:** Consumes final settings/manifest wiring; produces updated `CLAUDE.md`, `HARNESS.md`, and `specs/hook-surface-slim/SUMMARY.md` with SC-mapped Verify rows.
- **Action:** Update live hook tables for dispatcher and removed auto-test. Fill SUMMARY What-changed, Verify table with real exit codes and Criterion column, Rollback, Harness-Delta. Mark PLAN status shipped only after gates pass. Run lint-doc-truth and gate-modes smoke.
- **Verify:** `bash scripts/lint-doc-truth.sh`
- **Done:** Docs match settings/manifest; SUMMARY evidence complete for high-risk lane.

## 5. Risks

- Dispatcher swallows deny JSON → mitigated by SC-2 untracked deny case and existing untracked tests on the child script.
- `.claude` mode trust weaker than index → accepted in design; root index still wins; defaults CI-pinned.
- Deploy settings merge leaves stale four Bash hook commands in consumer `.claude/settings.json` → verify prune/merge behavior in deploy test; document re-sync.
- High-blast surface (`hooks/*`, `settings.json`) requires high-risk review chain before finish.

## 6. Status Log

- 2026-08-06 — research + design-ab; human approved default A+B choices; PLAN authored; execution not started.
- 2026-08-06 — implementation complete; suite ALL GREEN; finishing for PR.
