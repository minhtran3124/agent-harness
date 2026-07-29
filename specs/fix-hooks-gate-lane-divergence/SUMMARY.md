# fix-hooks-gate-lane-divergence — Summary

Lane: high-risk
Confidence: high
Reason: touches hooks/* (manifest high-blast hard gate) — Lane is forced regardless of the actual change size.
Flags: high-blast
Affects: hooks/risk-corroboration.sh, hooks/blast-radius-check.sh, hooks/scope-gate.sh, hooks/lib/
Input-type: harness improvement

### Intent

ok, let implement following the ranked fixes

(Full scope, from `docs/research/harness-review-improvements/reviews/hooks-gate-review-2026-07-29.md` §4:
1. Fix Lane-resolution divergence (F1, medium): `commit-quality-gate.sh` and `risk-corroboration.sh`
   resolve `Lane:` via two different strategies; `risk-corroboration.sh`'s disk-mtime fallback can
   attribute an unrelated spec's Lane to a commit that never touched `specs/`. Extract a shared
   `hooks/lib/lane.sh`.
2. Add session-scoped dedup to `scope-gate.sh` (low): it re-nudges on every qualifying message even
   after intake has already run for the in-flight task.
3. Fix stale doc: `break-glass-log.md`'s header still attributes the log solely to the deleted
   `protected-path-guard.sh`, when `branch-isolation-guard.sh` also writes to it.
Explicitly out of scope: `branch-guard.sh` (evidence refuted removing it), the 7 block-mode
risk-corroboration categories, and the already-loosened `workflow-engine`/`weakening-validation` modes.)

## What changed

Added `hooks/lib/lane.sh`, a shared helper providing `hook_lib_find_active_plan` (the
`status: active` PLAN.md lookup, previously duplicated ad hoc in `blast-radius-check.sh`) and
`hook_lib_resolve_lane` (staged-SUMMARY-first, else the active plan's sibling SUMMARY — never a bare
mtime guess). `risk-corroboration.sh` and `blast-radius-check.sh` now source it instead of each
carrying their own divergent logic. `scope-gate.sh` gained a git-native (no `find`/`stat`, portable)
in-progress check that skips the nudge once intake has already run or is mid-flight for the current
task. `break-glass-log.md`'s header now names both writers and both entry formats.

### Rationale

The plan's original idea (from the review doc) was a single shared Lane-resolution strategy for
*both* commit-quality-gate.sh and risk-corroboration.sh — but `commit-quality-gate.sh` Check 1.6
resolves Lane in **Python** (`scripts/verify_summary.py`), not bash, so there is no shared bash
function to extract there; its strict per-commit-touched-slug scoping is correct for its own purpose
(evidence completeness, not corroboration) and is left untouched. The real, fixable divergence was
between `risk-corroboration.sh`'s bash-native mtime fallback and the *pattern this codebase already
uses correctly elsewhere*: `blast-radius-check.sh`'s `status: active` PLAN.md lookup (itself written
specifically to replace an earlier "most recent on disk" bug — see
`docs/solutions/harness/stale-active-plan-misaims-blast-radius.md`). Reusing that exact signal for
`risk-corroboration.sh`'s fallback — instead of reinventing mtime scanning — closes the divergence
with a shared lib and makes `blast-radius-check.sh`'s existing inline loop reusable instead of
duplicated. The same "active plan" primitive doubles as a portable half of the `scope-gate.sh` dedup;
the other half (an uncommitted `specs/` change) is a `git status --porcelain` check, chosen
specifically to avoid `find -newermt`/`stat -f` vs `-c` portability traps — this machine's `find` is
actually `bfs`, which rejected GNU-style relative `-newermt` strings outright during implementation,
confirming that risk was real, not theoretical.

### Alternatives considered

- Session-scoped dedup for `scope-gate.sh` via a persistent per-session marker file (keyed by
  `session_id`, mirroring `state-breadcrumb.sh`) — rejected: adds a new stateful runtime convention
  for a hook the prior review rated "cheap, advisory, keep (borderline)"; disproportionate to the
  finding's severity (low).
- mtime-based "was `specs/*/SUMMARY.md` touched in the last N minutes" dedup signal — rejected after
  hitting the `bfs`/`-newermt` portability failure firsthand; replaced with the git-native
  `git status --porcelain -- specs` check (no new binary dependency, works identically cross-platform
  since git is already a hard dependency of every hook in this suite).
- Full `/brainstorming` → `/xia2` → `/writing-plans` ceremony via the skill chain — the Skill tool has
  no registered `feature-intake`/`writing-plans`/etc. entries in this session (this repo does not
  self-deploy to `.claude/skills/`), and the fix scope has a single, unambiguous interpretation
  already fully specified by the prior research doc — so intake/planning were done directly in this
  SUMMARY + a lightweight PLAN.md instead of invoking a skill wrapper that isn't wired up.

### Deviations

- none (Rule 1–3 auto-fixes) — the Lane-resolution scope narrowed from "both hooks" to
  "risk-corroboration.sh + blast-radius-check.sh" per the Rationale above; that's a plan refinement
  during implementation, not a Rule 1–3 auto-correct-scope event.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| syntax | `bash -n hooks/lib/lane.sh` | 0 | | |
| hook contract: risk-corroboration | `bash tests/hooks/risk-corroboration.test.sh` | 0 | all cases pass incl. new active-plan-fallback cases | SC-1 |
| hook contract: blast-radius-check | `bash tests/hooks/blast-radius-check.test.sh` | 0 | all cases pass, shared-lib refactor behavior-preserving | SC-2 |
| hook contract: scope-gate | `bash tests/hooks/scope-gate.test.sh` | 0 | all cases pass incl. new dedup cases | SC-3 |
| full harness suite | `bash scripts/run-tests.sh` | 0 | L1 syntax/lint/manifest + L2 hook contracts + L3 script tests all green | SC-4 |

### Rollback

- `git revert <sha>` — safe wholesale revert: this is a single self-contained commit
  touching only `hooks/lib/lane.sh` (new file, delete on revert),
  `hooks/risk-corroboration.sh`, `hooks/blast-radius-check.sh`, `hooks/scope-gate.sh`,
  `docs/harness-experimental/break-glass-log.md`, and their test files. No later commit
  depends on the new `hooks/lib/lane.sh` functions (nothing else in this branch sources
  it), so a plain revert restores each hook's prior inline logic byte-for-byte with no
  follow-up edits required.

### Harness-Delta

- fix-direct: closes F1 (Lane-resolution divergence) and the scope-gate.sh no-dedup gap identified in
  `docs/research/harness-review-improvements/reviews/hooks-gate-review-2026-07-29.md`.
