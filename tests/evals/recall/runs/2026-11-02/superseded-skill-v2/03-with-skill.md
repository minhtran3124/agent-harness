Verdict: known risk

**Do first.**
- Make each `### Verify` command pipe-free. Replace `grep -E "a|b"` with `grep -e a -e b`. Replace `X || Y` or `X && Y` with `X; a=$?; Y; b=$?; test "$a" = 0 -a "$b" = 0`. Replace `cmd | wc` with a redirect to a file. Source: `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md` (confirmed_at 2026-08-17). The record says a `|` inside the command is read as a column boundary, so the row never matches its claimed exit.
- Remove the whole-suite row (`bash scripts/run-tests.sh`). Put fast, specific checks in the table instead, such as one test file, a grep-guard or a lint. Write "covered by the CI `tests` job" in a prose note. The strict gate re-runs every Verify command under a 60s cap. Source: the same record (confirmed_at 2026-08-17).
- Lint the SUMMARY directly before you push. `run-tests.sh` skips its verify-row lint for uncommitted files. Source: `docs/solutions/harness/committed-diff-scoped-lint-skips-uncommitted-work.md` (confirmed_at 2026-08-12). Commands:
  - `python3 scripts/check_verify_rows.py specs/<slug>/SUMMARY.md`
  - `python3 scripts/verify_summary.py --lane <slug>`
  - `python3 scripts/verify_summary.py <slug> --check` (the strict-gate re-run)

**Avoid.**
- Do not paste a command that contains `||`, `&&`, `a|b` or `cmd | wc`. The parser cuts the command short or shifts the Exit column, and the row can never match its claimed exit. This happened 6 times in one session.
- Do not trust a local `ALL GREEN` from `run-tests.sh` when the SUMMARY is not yet committed. The lint prints `skip — no changed SUMMARY.md/PLAN.md`, then every CI job fails, with TIMEOUT `[Full suite]` in the strict gate.
- Do not write a Verify row that greps prose containing the phrase "full suite". The whole-suite detector matches that phrase anywhere in the cell, so the row fails L1. Use "whole suite" in rule prose, or pin a different substring.

**Check before done.**
- Run `check_verify_rows.py` on the SUMMARY path. It must find no `|` in a command and no whole-suite or build invocation.
- Run `verify_summary.py <slug> --check`. Every row must pass in under 60s on a cold run.
- If the SUMMARY is committed, re-run the suite so the L1 lint is in scope. A `skip` line is not a pass.

**Possibly stale.**
- `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md` and `docs/solutions/harness/committed-diff-scoped-lint-skips-uncommitted-work.md` are both more than 30 days old (2026-08-17 and 2026-08-12, today is 2026-11-02).
- Both records list `affects` paths that I could not find. A Glob for `verify_summary.py`, `ci-strict-gate.sh` and `check_verify_rows.py` returned nothing in this worktree. Only `scripts/run-tests.sh` exists. No `specs/*/SUMMARY.md` exists either. A Grep found them only in `tests/scripts/finishing-branch-contract.test.sh`, `docs/research/ste-terminology-evidence/DECISION.md`, `CHANGELOG.md` and the eval run files. I did not find a `plugins/harness/` copy.
- The premise (a pipe splits the row, and the cap is 60s) may still hold. The commands in the records may have moved or been removed, so check where the gate now lives before you run them.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`, `docs/solutions/harness/committed-diff-scoped-lint-skips-uncommitted-work.md`. Glob and Grep over the worktree for the `affects` paths and `specs/*/SUMMARY.md`.
