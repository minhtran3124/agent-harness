Verdict: known risk

**Possibly stale.**
- `docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md`: this is the record for your symptom, but it is stale. `confirmed_at` is 2026-09-29 (34 days old), and `hooks/commit-gate.sh` was removed in `4a9450c`. Its premise of a bare command in `settings.json` also no longer holds: `tests/scripts/settings-wiring.test.sh` now requires `settings.json` to wire no hooks and requires `plugins/harness/hooks/hooks.json` to use exec form (`bash` plus a script argument). Only the index mode `100755` check survives; the `[ -x ]` assertion the record cites is gone.
- `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md`: `confirmed_at` is 2026-07-17 (108 days old), `hooks/` and `templates/SUMMARY.template.md` are missing, and the record marks itself superseded.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md`, `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md`, `settings.json`, `tests/scripts/settings-wiring.test.sh`, `tests/lib.sh` (grep only), `git ls-files -s` for hook paths, `git log` for `hooks/commit-gate.sh`, `scripts/deploy-harness.sh` (grep failed, file missing). `plugins/harness/hooks/hooks.json` was not opened.
