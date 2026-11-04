Verdict: out-of-date match

**Possibly stale.**
- `docs/solutions/harness/gate-config-must-read-index.md` (confirmed_at 2026-07-23, 104 days old):
  - It ends with "Superseded by specs/simplify-hook-surface (2026-09-29)", because `risk-corroboration.sh` was merged into `hooks/commit-gate.sh`.
  - `hooks/risk-corroboration.sh`, `hooks/commit-gate.sh`, `tests/hooks/risk-corroboration.test.sh` and `harness-manifest.json` are all absent. A search under `plugins/harness/` found none of them.
- `docs/solutions/harness/consumer-risk-modes-index-safe.md` (confirmed_at 2026-08-06, 90 days old):
  - It carries the same superseded banner.
  - Its files `hooks/risk-corroboration.sh`, `hooks/lib/gate-modes.default.sh`, `harness-manifest.json` and `scripts/check_gate_modes_smoke.py` are absent.
- `docs/solutions/harness/gate-mode-as-data-decisions.md` (confirmed_at 2026-07-23, 104 days old):
  - It carries the same superseded banner.
  - Its files `hooks/risk-corroboration.sh`, `harness-manifest.json`, `scripts/check_manifest.py` and `scripts/check_gate_modes_smoke.py` are absent.

All three records describe your risk almost exactly: an unstaged worktree edit to the manifest loosens a commit hook's decision for the committed tree. Each one is superseded and depends on files that are not in this repo, so none goes in the action sections. Check the successor spec `specs/simplify-hook-surface` and the current commit-gate hook before you reuse their advice. I did not open either, and neither is in the repo or the index.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/gate-config-must-read-index.md`, `docs/solutions/harness/consumer-risk-modes-index-safe.md`, `docs/solutions/harness/gate-mode-as-data-decisions.md`. I also ran a read-only `ls`/`find`/`grep` for the `affects` paths in the repo root and under `plugins/harness/`.
