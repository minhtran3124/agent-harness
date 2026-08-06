# hook-surface-slim — Summary

Lane: high-risk
Confidence: high
Reason: implementation edits hooks/* and settings.json (high-blast block-mode); B3 changes consumer risk-mode fallback (embedded defaults, no .claude read).
Flags: high-blast, workflow-engine, existing-behavior
Affects: hook-registration (settings.json), hard-gate-vocabulary, commit-time and edit-time gates
Input-type: harness improvement
Route: design approved (corrected B3-only) → PLAN.md active → using-git-worktrees (feat/hook-surface-slim-b3) → subagent-driven-development → simplify → correctness/intent → receipt
Escalate: no — human approved corrected A+B (B3-only) package (2026-08-06)

### Intent

hiện tại thì tôi cảm giác có quá nhiều ràng buộc hooks khi implement 1 feature cho chính harness repo này là 1, stuck cũng nhiều nếu install ở 1 repo khác và làm 1 feature mới trên feature đó.

hãy review/research lại hệ thống hook của harness repo hiện tại. xem thử có chỗ nào chúng ta có thể remove bớt để giảm bớt gánh nặng của việc chạy quá nhiều hooks, làm cho perf nhanh hơn.

ok, approve default recommend

## What changed

Implemented the corrected **B3-only** Package A+B on branch `feat/hook-surface-slim-b3` (base 30dc501), in 3 waves, 6 tasks:

- **A1-thin** — collapsed the 4 PreToolUse Bash hooks into one `hooks/pre-bash-dispatch.sh` (1 spawn on non-commit Bash; fans out on commit/push, relaying every sub-hook's stdout unconditionally). Commit d93c085.
- **A2e** — `hook_lib_find_active_plan` short-circuit (one `grep -l` instead of N greps). Commit 4c0228c.
- **A4-opt-in** — commit-quality Checks 2/2.5/3 gated behind `REQUIRE_APP_GATES=1` (off by default; **not** the rejected A4-detect). Commit 7bc23b5.
- **A3** — deleted dormant `auto-test-on-change.sh` + reconciled `harness-manifest.json`/`CLAUDE.md`. Commit 6d2cb4f.
- **B3-only** — `hooks/lib/gate-modes.default.sh` embedded defaults + `risk-corroboration.sh` resolves modes ONLY from the git index (`git show :`) or embedded defaults, **never `.claude/`** (avoids TOCTOU #160). Consumers fall back to 2-warn/7-block parity, not block-all. Commit 570c69d + docs 505f6ec, a098af1.
- **Deploy prune-on-merge** (task 4.1) — `derive_settings` now prunes source-removed harness hooks on an in-place upgrade so the retired 4 Bash hooks don't double-register alongside the dispatcher; foreign hooks preserved. Commit 83045b1.

Final gates: simplify (clean, no mutation), correctness-review (no Critical/High/Medium bugs), intent-review (FULFILLED). Full suite ALL GREEN.

### Rationale

Highest ROI without loosening true hard gates: cut the always-on Bash spawn tax and give consumers meta-repo parity via embedded defaults compiled into the hook — index-safe, no deploy-copied policy file.

### Alternatives considered

- A1-lib / A2a marker / B1 root manifest / B5 docs-only — rejected; see `design.md` §9 / `design-ab.md` §5.
- **B-hybrid / A4-detect** — rejected after review: B-hybrid read `.claude/harness-manifest.json` (reopens critical TOCTOU #160); A4-detect fired pytest on any repo with an `app/` dir. Replaced by B3-only + A4-opt-in.
- Package E (simplify/task-review ceremony) — deferred, separate initiative.

### Deviations

- Rule 1 (task 1.2) — `hook_lib_find_active_plan` multi-active tie-break changed from mtime (`ls -t`) to lexical glob order; documented in the function comment; single/zero-active behavior byte-identical. Commit 4c0228c.
- Rule 2 (task 1.3) — existing Check 2/2.5/3 tests updated to pass `REQUIRE_APP_GATES=1` so they still exercise the now-gated checks. Commit 7bc23b5.
- Rule 1 (task 2.1) — four dispatched hooks kept as non-✅ "↳ dispatched" CLAUDE.md rows (lint-doc-truth needs a row per on-disk hook). Commit 6d2cb4f.
- Rule 1 (task 3.1) — 3 workflow-engine tests flipped block→warn (necessary consequence of embedded 2-warn/7-block parity replacing block-all). Commit 570c69d.
- Post-review (intent finding) — removed stale `auto-test-on-change` reference from `rules/auto-correct-scope.md` tiny-lane safety-net list.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| dispatcher deny-relay | `bash tests/hooks/pre-bash-dispatch.test.sh` | 0 | untracked-py deny (exit 0 + stdout JSON) survives dispatch | SC-1 |
| single Bash registration | `python3 -c "import json,sys; s=json.load(open('settings.json')); n=sum(1 for e in s['hooks']['PreToolUse'] if e.get('matcher')=='Bash' for _ in e['hooks']); sys.exit(0 if n==1 else 1)"` | 0 | exactly one PreToolUse Bash hook | SC-2 |
| commit chain intact | `bash tests/hooks/gate-integration.test.sh` | 0 | secrets/escalation/lane still block via dispatcher | SC-3 |
| blast fast-path | `bash tests/hooks/blast-radius-check.test.sh` | 0 | 0-active silent; active scopes files | SC-4 |
| auto-test removed | `test ! -e hooks/auto-test-on-change.sh` | 0 | dormant hook deleted | SC-5 |
| app-gate opt-in | `bash tests/hooks/commit-quality-gate.test.sh` | 0 | Checks 2/2.5/3 skipped unless REQUIRE_APP_GATES=1 | SC-6 |
| embedded parity | `bash tests/hooks/warn-mode-smoke.test.sh` | 0 | no manifest → 2 warn / 7 block | SC-7 |
| .claude bypass guard | `bash tests/hooks/risk-corroboration.test.sh` | 0 | all-warn .claude does NOT loosen auth | SC-8 |
| gate-modes drift | `python3 scripts/check_gate_modes_smoke.py` | 0 | defaults == manifest detectable | SC-9 |
| inventory consistency | `python3 scripts/check_manifest.py` | 0 | manifest ↔ settings ↔ CLAUDE.md | SC-10 |
| deploy prune-on-merge | `bash tests/scripts/settings-merge.test.sh` | 0 | in-place upgrade prunes source-removed harness hooks; foreign hooks survive | SC-11 |
| lane intake | `python3 scripts/verify_summary.py --lane hook-surface-slim` | 0 | high-risk evidence present | |

### Rollback

- Undo the whole branch: `git checkout simplify` and discard `feat/hook-surface-slim-b3` (no merge to main yet).
- Or revert the implementation range: `git revert --no-commit 30dc501..HEAD` on a branch.
- Refresh derived harness after any revert: `bash scripts/deploy-harness.sh --target <repo root>`.

### Harness-Delta

- fix-direct — **FIXED in task 4.1** (commit 83045b1). `derive_settings` in `scripts/deploy-harness.sh` now prunes any prior harness hook registration (command under `$CLAUDE_PROJECT_DIR/.claude/hooks/`), not just the current source set, so an **in-place consumer upgrade** drops the 4 old Bash registrations instead of double-registering them alongside the dispatcher. Consumer-owned foreign hooks (other paths) survive. Covered by SC-11.
