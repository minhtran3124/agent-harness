Verdict: known risk. A dormant file under `hooks/` is classed high-risk because the gate keys on path, not on wiring. The gate and tooling that record describes are not in this repo, so its mechanics are out of date.

**Do first**
1. Before you write the hook, answer two design questions in the SUMMARY Rationale or design.md. Does it fail safe and visibly? Is the task worth a standing cost, and can it be checked pass/fail with few false alarms? If either answer is no, use a one-off script instead. Use `|| true` on the command for advisory work, not a try/except list. Source: `docs/solutions/harness/automation-readiness.md` (confirmed_at 2026-07-17).
2. Ship the hook dormant and leave the `settings.json` wiring to a separate step that needs human confirmation. Registering a hook in `settings.json` is a high-blast change. Track the pending activation so it is not forgotten. Source: `docs/solutions/harness/gap-closure-decisions.md`, Decision 2 (confirmed_at 2026-07-17).
3. Declare the high-risk lane up front, with real Verify and Rollback blocks in the SUMMARY. Do not argue the hook down to a lower lane because it is dormant. The principle still holds, but the commands that record gives are stale (see Possibly stale). Source: `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md` (confirmed_at 2026-07-17).

**Check before done**
- Dormancy does not exempt the hook from the path-keyed gate. The high-risk SUMMARY must exist before the commit, not after the gate rejects it.
- The hook is not a replacement for the high-blast gate. `automation-readiness` is a design layer on top of it, not a risk reclassification.
- If the hook is ever registered as a bare command, it must be mode 100755 in the index. This comes from `bare-command-hook-must-be-executable-in-index` in `critical-patterns.md`, which I did not open, so I have not checked it against this repo.

**Already decided**
- `docs/solutions/harness/gap-closure-decisions.md`: default to shipping a new hook dormant, and gate the `settings.json` wiring as its own step.

**Possibly stale**
- `hooks-addition-is-high-risk-even-dormant.md` is marked superseded. It says `risk-corroboration.sh` was merged into `commit-gate.sh`.
- `hooks/commit-gate.sh` and `hooks/risk-corroboration.sh` are not present. Under `plugins/harness/hooks/` I found only `clean-worktrees.sh`, `merge-guard.sh`, `pr-opened.sh`, `secrets-scan.sh`, `session-rules.sh` and `hooks.json`.
- A search of `plugins/harness` for `high-risk`, `high-blast` and `^hooks/` matched only `skills/recall/evals/evals.json`. I did not find the `^hooks/` gate here, so the "gate rejects it" behaviour may not apply in this layout.
- The `python scripts/verify_summary.py --lane/--check` commands are out of date because `verify_summary.py` was not found anywhere under `plugins/harness/`. The same applies to `templates/SUMMARY.template.md`. Only the principle holds.
- `hooks/protected-path-guard.sh` was not found, so that `affects` path is missing. The dormant-hook decision does not depend on it.
- All three records are about 110 days old (confirmed_at 2026-07-17, today 2026-11-04), so each is over 30 days old.
- The root-level `hooks/` and `scripts/` paths do not exist in this worktree. The harness is under `plugins/harness/`, so the records may describe an older layout.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md`, `docs/solutions/harness/gap-closure-decisions.md`, `docs/solutions/harness/automation-readiness.md`. I also checked `plugins/harness/hooks/` and the `plugins/harness` tree with Grep, Glob and a directory listing.
