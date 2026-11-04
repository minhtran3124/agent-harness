Verdict: known risk (both matching records are stale, so neither gives actions here)

**Possibly stale.**
- `docs/solutions/harness/hook-root-must-not-come-from-install-location.md`: `confirmed_at` 2026-09-09 is 54 days old, and all 8 `affects` paths under `hooks/` are missing because the hooks now live in `plugins/harness/hooks/` (the top-level `hooks/` path matched no scripts).
- `docs/solutions/harness/ratchet-matches-spelling-not-property.md`: `confirmed_at` 2026-09-09 is 54 days old, and `hooks/session-knowledge.sh` and `tests/hooks/repo-root-resolution.test.sh` are missing; `scripts/check-hook-root-source.sh` exists but now scans only `plugins/harness/hooks/`.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/hook-root-must-not-come-from-install-location.md`, `docs/solutions/harness/ratchet-matches-spelling-not-property.md`; Glob and Grep only, not read in full: `hooks/`, `plugins/`, `scripts/`, and a repo-wide filename Glob for `check-hook-root-source.sh`, `repo-root-resolution.test.sh` and `session-knowledge.sh`.
