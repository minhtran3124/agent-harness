# hook-surface-slim — Summary

Lane: high-risk
Confidence: high
Reason: implementation edits hooks/* and settings.json (high-blast block-mode); risk mode delivery touches deploy + hard-gate vocabulary consumers.
Flags: high-blast, workflow-engine, existing-behavior
Affects: hook-registration (settings.json), hard-gate-vocabulary, commit-time and edit-time gates, deploy-harness
Input-type: harness improvement
Route: design approved → PLAN.md → worktree feat/hook-surface-slim → implement A→B
Escalate: no — human approved default A+B package (2026-08-06)

### Intent

hiện tại thì tôi cảm giác có quá nhiều ràng buộc hooks khi implement 1 feature cho chính harness repo này là 1, stuck cũng nhiều nếu install ở 1 repo khác và làm 1 feature mới trên feature đó.

hãy review/research lại hệ thống hook của harness repo hiện tại. xem thử có chỗ nào chúng ta có thể remove bớt để giảm bớt gánh nặng của việc chạy quá nhiều hooks, làm cho perf nhanh hơn.

ok, approve default recommend

## What changed

Package A+B shipped on `feat/hook-surface-slim`:

- **A1:** `hooks/pre-bash-dispatch.sh` is the sole Bash PreToolUse entry; four former gates remain as child scripts (`wired: false`).
- **A2e:** `hook_lib_find_active_plan` short-circuits without `ls -t` full-tree sort.
- **A3:** deleted dormant `auto-test-on-change.sh` + tests.
- **A4:** commit-quality Checks 2/2.5/3 run only when root `app/` exists.
- **B-hybrid:** risk modes resolve index → root worktree → `.claude/harness-manifest.json` → `hooks/lib/gate-modes-default.sh`; deploy copies manifest into `.claude/`; defaults CI-pinned via `generate_gate_modes_default.py`.
- Deploy settings merge prunes retired harness hooks under `.claude/hooks/`.

### Rationale

Cut always-on Bash multi-spawn tax and give consumers the same risk warn/block modes as the meta-repo without loosening true hard gates.

### Alternatives considered

- A1-lib / A2a marker / B1 root manifest / B5 docs-only — rejected; see `design.md` §9.
- Package E (simplify/task-review ceremony) — deferred.

### Deviations

- Rule 3 — deploy merge kept retired Bash hooks as "foreign"; fixed by stripping any prior `$CLAUDE_PROJECT_DIR/.claude/hooks/*` command not in the new harness set.
- Rule 1 — risk-corroboration workflow-engine unit tests expected consumer fail-closed block; updated to expect default warn parity (block path still covered with staged mode=block).

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| manifest wiring | `python3 scripts/check_manifest.py` | 0 | dispatcher wired; children false; auto-test gone | SC-1 |
| bash dispatcher | `bash tests/hooks/pre-bash-dispatch.test.sh` | 0 | 6 passed | SC-2 |
| blast / active-plan | `bash tests/hooks/blast-radius-check.test.sh` | 0 | 12 passed | SC-3 |
| manifest after A3 | `python3 scripts/check_manifest.py` | 0 | same as SC-1 | SC-4 |
| commit-quality app gate | `bash tests/hooks/commit-quality-gate.test.sh` | 0 | 30 passed | SC-5 |
| warn-mode + defaults | `bash tests/hooks/warn-mode-smoke.test.sh` | 0 | 5 passed | SC-6 |
| deploy modes artifact | `bash tests/scripts/deploy-manifest-modes.test.sh` | 0 | 1 passed | SC-7 |
| doc-truth | `bash scripts/lint-doc-truth.sh` | 0 | hook table matches settings | SC-8 |
| gate-modes pin | `python3 scripts/check_gate_modes_smoke.py` | 0 | defaults ↔ manifest | SC-6 |

### Rollback

- `git revert` the implementation commit(s) on `feat/hook-surface-slim`; re-run `bash scripts/deploy-harness.sh` so consumers drop dispatcher and restore prior settings shape.

### Harness-Delta

- fix-direct — consumer missing-manifest block-all; Bash multi-spawn always-on; deploy merge stale harness hooks
