Verdict: existing decision

**Do first**
- Ship the hook dormant and put the `settings.json` wiring in a separate, human-confirmed step. Editing hook registration in `settings.json` is itself a high-blast change. Source: docs/solutions/harness/gap-closure-decisions.md (Decision 2, confirmed_at 2026-07-17).
- Before you write the hook, answer two questions in design.md or the SUMMARY Rationale. Does it fail safe and visibly? That means a finite retry and `… || true` on the command, not a try/except allowlist. Does the task recur enough, and can you check its output pass or fail? If either answer is no, use a one-off script. Source: docs/solutions/harness/automation-readiness.md (confirmed_at 2026-07-17).

**Avoid**
- Do not expect a hook to leave the high-risk lane because it is not in `settings.json`. The old gate matched on the path, not on whether the hook was wired. If the lane was declared lower, the commit was blocked. Source: docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md. That record is out of date (see Possibly stale), so confirm the current behavior in the repo.

**Check before done**
- The hook is not in `settings.json`, and the new file's mode is correct for when you do wire it. A bare-command hook that is not executable fails open. I did not open `bare-command-hook-must-be-executable-in-index`, so check its record before you wire the hook.

**Already decided**
- docs/solutions/harness/gap-closure-decisions.md: new hooks ship dormant by default, with `settings.json` wiring as a separate Rule-4 step. The CLAUDE.md hook table marks them `⬜ dormant`. A dormant hook with no scheduled wiring can be forgotten, so track the pending activation.

**Possibly stale**
- docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md: out of date.
  - It says it is superseded by specs/simplify-hook-surface, which merged `risk-corroboration.sh` into `commit-gate.sh`.
  - Neither `hooks/risk-corroboration.sh` nor `hooks/commit-gate.sh` exists in this repo.
  - `scripts/verify_summary.py` and `templates/SUMMARY.template.md` are also missing. The record's commands depend on them.
  - `hooks/` now lives at `plugins/harness/hooks/`.
  - Its confirmed_at is 2026-07-17, more than 30 days ago.
- docs/solutions/harness/gap-closure-decisions.md: more than 30 days old (confirmed_at 2026-07-17).
  - The `affects` paths `hooks/protected-path-guard.sh` and the `docs/research/...` file are missing.
  - The root `settings.json` exists.
  - The advice does not depend on the missing paths, so I kept it in the parts above.
- docs/solutions/harness/automation-readiness.md: more than 30 days old (confirmed_at 2026-07-17).
  - The root `hooks/` path moved to `plugins/harness/hooks/`.
  - `.github/workflows/` exists.
  - The advice still holds.

**Search surface:** docs/solutions/INDEX.md, docs/solutions/critical-patterns.md, docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md, docs/solutions/harness/gap-closure-decisions.md, docs/solutions/harness/automation-readiness.md. Path checks: `ls` of the repo root, `hooks/`, `plugins/harness/hooks/`, `plugins/harness/scripts/` and `.github/workflows/`. Glob for `commit-gate.sh`, `risk-corroboration.sh`, `protected-path-guard.sh`, `verify_summary.py` and `SUMMARY.template.md`. Grep for `high-risk` and `^hooks/`.
