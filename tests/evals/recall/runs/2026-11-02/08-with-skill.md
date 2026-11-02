Verdict: known risk, but the records' premise (a path-keyed `hooks/` gate) does not match this repo, so treat them as background only.

**Do first.**
- Ask whether the new hook should exist as a standing automation. Answer two questions in design.md or the SUMMARY Rationale: does it fail safe and loud (finite retry, `|| true` on the command), and is its output objectively checkable with low false alarm? If either answer is no, prefer a one-off script. Source: `docs/solutions/harness/automation-readiness.md` (confirmed_at 2026-07-17). It gives no command.
- Keep the hook unwired, as you plan. Wiring it into `settings.json` is a separate step that needs human confirmation. Source: `docs/solutions/harness/gap-closure-decisions.md`, Decision 2 (confirmed_at 2026-07-17). It gives no command.

**Avoid.**
- Do not treat the high-risk lane as a false positive just because the hook is not wired. The old record says the corroboration gate keyed on the `^hooks/` path, not on registration. Declaring a lane below `high-risk` blocked the commit. Source: `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md`.

**Check before done.**
- If the hook is later registered as a bare command, confirm it is committed as mode 100755. A 100644 file exits 126 and silently fails open. Source: `docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md`, summarised in `critical-patterns.md`. I did not open that record.
- If the lane stays `high-risk`, check that the SUMMARY has non-placeholder Verify and Rollback blocks, and that the Verify rows have no pipes and run in under 60 seconds (`critical-patterns.md`, `verify-row-must-be-pipe-free-and-under-60s`). The old record's validation commands (`python scripts/verify_summary.py --lane <slug>` and `--check <slug>`) point at a script that is not in this repo (`scripts/verify_summary.py`), so I could not confirm they still work.

**Already decided.**
- `docs/solutions/harness/gap-closure-decisions.md`: a new hook ships dormant, and the `settings.json` wiring is a separate Rule-4-gated step.

**Possibly stale.**
- `hooks-addition-is-high-risk-even-dormant.md` is marked superseded by `specs/simplify-hook-surface` (2026-09-29), because `risk-corroboration.sh` was merged into `hooks/commit-gate.sh`. It is about 108 days old (2026-07-17 to 2026-11-02). Its `affects` path `hooks/` is not at the repo root, and `templates/SUMMARY.template.md` is missing. Neither `commit-gate.sh` nor `risk-corroboration.sh` exists anywhere in this worktree. I found no `high-blast`, `high-risk` or `^hooks` match under `plugins/harness/` except in `skills/recall/evals/evals.json`. The root `settings.json` has no `hooks`, `risk` or `lane` text. The "gate keys on path" premise is not confirmed here, so confirm where the gate now lives before you rely on it.
- `gap-closure-decisions.md` is about 108 days old. Its `affects` paths `hooks/protected-path-guard.sh` and the research doc are missing, and the root `settings.json` exists but has no hook registration. Hooks now live at `plugins/harness/hooks/` (registered via `hooks.json`). Decision 2's reasoning may still hold, but it names `settings.json` where this repo uses `hooks.json`.
- `automation-readiness.md` is about 108 days old. Its `affects` path `hooks/` is not at the root (the hooks are under `plugins/harness/hooks/`). Its design questions are still valid.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/hooks-addition-is-high-risk-even-dormant.md`, `docs/solutions/harness/gap-closure-decisions.md`, `docs/solutions/harness/automation-readiness.md`. Existence checks only: `plugins/harness/hooks/` listing, a Glob for `commit-gate.sh`, `risk-corroboration.sh`, `protected-path-guard.sh`, `SUMMARY.template.md` and `verify_summary.py`, a Grep of `plugins/harness/` for gate terms, and a Grep of the root `settings.json`.
