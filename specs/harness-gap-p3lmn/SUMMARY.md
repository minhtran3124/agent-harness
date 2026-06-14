# harness-gap-p3lmn — Summary

Lane: high-risk
Confidence: high
Reason: Adds a new file under hooks/ (protected-path-guard.sh) — a high-blast path per rules/auto-correct-scope.md Rule 4 — so the change is high-risk even though the hook ships dormant (unregistered). Human-authorized.
Flags: high-blast (hooks/)
Affects: hooks/ (new dormant hook) + CLAUDE.md hook table + installer PAYLOAD
Input-type: harness improvement

### Intent

Phase 3 of the harness gap-closure plan: build P3-L (break-glass protected-path hook) and P3-N (VERSION/CHANGELOG), continuing on a new branch after P3-J/K merged. P3-M found already-shipped.

## What changed

Added `hooks/protected-path-guard.sh` (dormant PreToolUse hook that hard-blocks writes to high-blast files unless `PROTECTED_PATH_REASON` is set, with a break-glass audit log) + 8 contract tests + a ⬜ dormant row in the CLAUDE.md hook table. Added root `VERSION` (0.1.0) and `CHANGELOG.md`, wired into the installer PAYLOAD + completion echo, with a CHANGELOG/VERSION bump step in the finishing skill.

### Rationale

The hook ships dormant (not registered in settings.json) so it changes no runtime behavior — wiring it is a separate Rule-4 step the user must authorize. This keeps the high-blast surface inert while the script + tests land. Lane is high-risk because adding any `hooks/*` file trips the corroboration gate regardless of dormancy.

### Alternatives considered

- Wire the hook immediately: rejected — wiring settings.json is a Rule-4 change needing explicit confirmation; dormant-first matches the auto-test-on-change precedent.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| full suite | `bash scripts/run-tests.sh` | 0 | bash contract tests (protected-path-guard 8 passed) + 102 python units; ALL GREEN |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | dormant ⬜ row present, not in settings.json; break-glass-log path exists |

### Rollback

- Revert the commit: `git revert <sha>`
- The hook is dormant (absent from settings.json) — no hook registration to undo.

### Harness-Delta

- backlog — the `check-untracked-py` hook denies an entire Bash call whose command string contains `git commit` while any untracked `.py` exists, even when the same call would `git add` them first. Worth a `/compound` note: stage and commit in separate tool calls.
