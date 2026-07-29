---
slug: fix-hooks-gate-lane-divergence
status: active
owner: minhtran3124
created: 2026-07-29
---

# Fix hooks gate Lane-resolution divergence + scope-gate nag dedup

## 1. Motivation

`docs/research/harness-review-improvements/reviews/hooks-gate-review-2026-07-29.md` found a real,
previously-undocumented latent bug (F1): `risk-corroboration.sh` resolves the declared `Lane:` via a
"most-recently-modified `specs/*/SUMMARY.md` on disk" fallback, which can attribute an unrelated
spec's Lane to a commit that never touched `specs/` at all. It also found that `scope-gate.sh` has no
dedup and re-nudges on every qualifying message even after intake has already resolved a lane for the
in-flight task. Both are fixable without touching the 7 block-mode risk-corroboration categories,
`branch-guard.sh`, or the already-loosened `workflow-engine`/`weakening-validation` modes.

## 2. Non-goals

- Do not touch `commit-quality-gate.sh` Check 1.6 or `scripts/verify_summary.py` — their per-commit,
  per-touched-slug scoping is correct for evidence-completeness and is a different concern from
  corroboration-fallback.
- Do not remove or narrow `branch-guard.sh` — the review's own real-case research refuted that.
- Do not loosen or tighten any `harness-manifest.json` gate mode.
- Do not add a persistent/stateful session-marker mechanism for `scope-gate.sh` — see SUMMARY.md
  "Alternatives considered."

## 3. Success Criteria

| ID | Behavior (observable) | Check (re-runnable) | Expected |
|------|-------------------------|-----------------------|------------|
| SC-1 | `risk-corroboration.sh` no longer borrows an unrelated spec's Lane for a commit that touches no `specs/` path; it still prefers a staged SUMMARY and falls back only to the `status: active` plan | `bash tests/hooks/risk-corroboration.test.sh` | exit 0 |
| SC-2 | `blast-radius-check.sh` behavior is unchanged after switching to the shared active-plan lookup (pure refactor) | `bash tests/hooks/blast-radius-check.test.sh` | exit 0 |
| SC-3 | `scope-gate.sh` skips its nudge once an active plan exists or `specs/` has an uncommitted change, and still fires when neither is true | `bash tests/hooks/scope-gate.test.sh` | exit 0 |
| SC-4 | Full harness suite (syntax, doc-truth lint, manifest consistency, all hook + script contract tests) stays green | `bash scripts/run-tests.sh` | exit 0 |

## 4. Tasks

### Task 1.1 — Shared lane/active-plan lib (wave 1)

- **Files:** hooks/lib/lane.sh
- **Action:** Create `hooks/lib/lane.sh` with two functions: `hook_lib_find_active_plan <repo_dir>`
  (the `status: active` `specs/*/PLAN.md` lookup, ported verbatim in behavior from
  `blast-radius-check.sh`'s existing inline loop) and `hook_lib_resolve_lane <repo_dir>
  <staged_paths>` (prefers a staged `SUMMARY.md`'s `Lane:` via `git show ":<path>"`, else falls back
  to the active plan's sibling `SUMMARY.md` — never a bare mtime scan). Follow the header-comment and
  bash-3.2-compatibility conventions of `hooks/lib/git-command.sh`.
- **Verify:** `bash -n hooks/lib/lane.sh`
- **Done:** File exists, sources cleanly, both functions defined.

### Task 1.2 — Wire risk-corroboration.sh to the shared lib (wave 2)

- **Files:** hooks/risk-corroboration.sh
- **Action:** Source `hooks/lib/lane.sh` alongside the existing `hooks/lib/git-command.sh` source
  (same fail-closed convention: missing lib → block with a "redeploy harness" message, matching how
  this hook already treats a missing `git-command.sh`). Replace the inline Lane-resolution block
  (staged-SUMMARY loop + `ls -t specs/*/SUMMARY.md` mtime fallback) with a single call to
  `hook_lib_resolve_lane "$REPO_DIR" "$STAGED_PATHS"`.
- **Verify:** `bash tests/hooks/risk-corroboration.test.sh`
- **Done:** Existing test cases still pass; a new case proves a commit touching no `specs/` path no
  longer corroborates against an unrelated, merely-recently-touched spec's Lane, but still
  corroborates against the `status: active` plan's Lane when one exists.

### Task 1.3 — Wire blast-radius-check.sh to the shared lib (wave 2)

- **Files:** hooks/blast-radius-check.sh
- **Action:** Source `hooks/lib/lane.sh`. Replace the inline `for p in $(ls -t
  "$REPO_DIR"/specs/*/PLAN.md ...)` loop with `PLAN=$(hook_lib_find_active_plan "$REPO_DIR") || exit
  0`. Pure refactor — behavior must be identical (this hook is warn-only by default; a missing lib
  should fail OPEN — silent exit 0 — not block, consistent with its own philosophy).
- **Verify:** `bash tests/hooks/blast-radius-check.test.sh`
- **Done:** All existing cases pass unchanged (behavior-preserving refactor, no new cases required).

### Task 1.4 — scope-gate.sh dedup via the shared lib + git status (wave 2)

- **Files:** hooks/scope-gate.sh
- **Action:** Add `SCRIPT_DIR`/`REPO_DIR` resolution (matching the other hooks' convention) and source
  `hooks/lib/lane.sh` with a `command -v` guard (missing lib → skip the dedup check, fall through to
  today's always-nag behavior — safe default since the nudge is non-blocking). Add
  `hook_lib_intake_in_progress <repo_dir>` to `hooks/lib/lane.sh` (Task 1.1 file, but this task adds
  the function since it's `scope-gate.sh`-specific and only makes sense once the call site exists):
  exit 0 when `hook_lib_find_active_plan` finds a plan, OR `git -C <repo_dir> status --porcelain --
  specs` reports any uncommitted change. Before injecting the nudge, skip (silent exit 0) if
  `hook_lib_intake_in_progress "$REPO_DIR"` is true.
- **Verify:** `bash tests/hooks/scope-gate.test.sh`
- **Done:** Existing cases still pass; new cases prove the nudge is skipped when an active plan
  exists, and skipped when `specs/` has an uncommitted file, while an implementation-intent prompt
  with neither still nudges as before.

### Task 2.1 — Fix stale break-glass-log.md header (wave 1)

- **Files:** docs/harness-experimental/break-glass-log.md
- **Action:** Rewrite the header to name both current writers — `branch-isolation-guard.sh`
  (`BRANCH_ISOLATION_REASON`, currently wired) and note `protected-path-guard.sh` was deleted in PR
  #133 (2026-07-21) and no longer writes here — and document both entry formats actually emitted (the
  bullet each hook's `printf`/`echo` produces), not the single generic format the old header claimed.
- **Verify:** `grep -q "branch-isolation-guard.sh" docs/harness-experimental/break-glass-log.md`
- **Done:** Header accurately reflects the current, real writer(s) and entry format(s).

## 5. Risks

- `risk-corroboration.sh` and `blast-radius-check.sh` are both block/warn gates that run on every
  commit / every edit respectively — a regression here has wide blast radius. Mitigated by running
  the full existing contract-test suites (not just new cases) before commit, per SC-1/SC-2/SC-4.
- `hook_lib_find_active_plan`'s behavior must stay byte-for-byte equivalent to
  `blast-radius-check.sh`'s current inline loop, or SC-2's existing test cases will catch a
  regression immediately (no new cases needed there precisely because the existing suite is the
  regression guard).

## 6. Status Log

- 2026-07-29 — plan created, work started same session.
