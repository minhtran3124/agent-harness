# gh-318-diagnosing-bugs — Review ledger

Controller ledger for per-task review results. It holds what goes into `SUMMARY.md` at finish.
SUMMARY stays uncommitted until every Success Criterion has a Verify row, because the commit gate
runs `verify_summary.py --lane` on a staged SUMMARY.

## Minor findings (task review, for the final review chain)

- Task 1.1 — `skills/diagnosing-bugs/SKILL.md` Phase 3, 4 and 6 `Done when:` lines leave out a criterion that the phase body states (posted to the user; diagnosis.md committed; leftover harness deleted). No behavior is lost. The file has 6 words of headroom.
- Task 1.1 — `references/diagnosis-review-prompt.md` return YAML has no `meaning:` and no `checked_against:` keys, which `rules/review-policy.md` names for the task reviewer.
- Task 1.1 — Only a template comment keeps the probe tag unbracketed in `diagnosis.md` `Probes:`. A bracketed tag there would match the Phase 6 `[DEBUG-` search.
- Task 1.2 — `task-reviewer-prompt.md` step 4 skip depends on `diagnosis.md` `Seam:`, but the reviewer's inputs do not say where it reads that line.
- Task 1.2 round 1 Minors 1–3 (exemption trigger, plan-format "Otherwise", named `NEEDS_CONTEXT` rule) were fixed in `28b9aa2` and re-reviewed clean.

## Fix rounds

- Task 1.2 — round 1 (`28b9aa2`): three Minors applied; re-review pass/approved, no findings.
- Task 1.3 — round 1 (`52b3416`): Important spec finding fixed (seam point compared with the whole `diagnosis.md` `Seam:` value); re-review pass/approved, no findings.

## Harness-Delta

- backlog (Task 1.1): in a worktree-isolated session the sandbox refuses compound shell lines, `cd`-prefixed lines and `$?` chains, so each check runs as its own call. The implementer brief could say so up front.
