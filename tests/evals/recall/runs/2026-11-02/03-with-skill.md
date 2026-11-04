Verdict: known risk

**Do first**
- Make every `### Verify` command pipe-free: no `|`, `||` or `a|b`. Use `grep -e a -e b`. For chains, use `X; a=$?; Y; b=$?; test "$a" = 0 -a "$b" = 0`. For `cmd | wc`, redirect to a file and read the file back. Source: docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md (confirmed_at 2026-08-17). The reason is that the parser splits each row on `|`, so a pipe becomes an extra column.
- Replace the whole-suite command with a fast, specific check that runs in under 60s: one test file, a grep guard, a lint or a single re-run. Cite the whole suite in prose as covered by the CI `tests` job. Same record (confirmed_at 2026-08-17). The strict gate re-runs each Verify command under a 60s cap, which matches Guardrail 3 of plan-format.
- Do not use the phrase "full suite" in any Verify cell, even in a grep of prose. The detector matches that literal text anywhere in the cell. Use "whole suite" or pin a different substring. Same record (confirmed_at 2026-08-17).

**Avoid**
- A pipe or `||` in a Verify command. The row can never match its claimed exit, and the parser reports `MISMATCH claimed=None` even when the command is correct.
- A Verify row such as `bash scripts/run-tests.sh`. It TIMEOUTs on cold CI and the strict gate blocks the PR.
- Reading a local `ALL GREEN` as proof that CI will pass for an uncommitted SUMMARY. The lint scope covers only committed files, so it prints `skip` and then fails every CI job (docs/solutions/harness/committed-diff-scoped-lint-skips-uncommitted-work.md, confirmed_at 2026-08-12).

**Check before done**
- Lint the file directly before you push: `python3 scripts/check_verify_rows.py specs/<slug>/SUMMARY.md`. The committed-diff record says the result is the same whether or not the file is committed. See the Possibly stale part: this script is not in the repo.
- Re-run the Verify rows under the 60s cap: `python3 scripts/verify_summary.py <slug> --check`. This is what the strict gate re-runs. The script is also not in the repo, so use the principle: time each row by hand and confirm it finishes in under 60s.
- Look in the run output for `skip — no changed SUMMARY.md/PLAN.md`. Treat it as "not checked", not as "passed".

**Possibly stale**
- `scripts/check_verify_rows.py`, `scripts/verify_summary.py`, `scripts/ci-strict-gate.sh` and `scripts/resolve-base-ref.sh` are not under `scripts/` or `plugins/`. A name search of the whole worktree found only `scripts/run-tests.sh`. The commands in the two records that name these scripts cannot be run here. The principles (pipe-free, under 60s, lint the path directly) still hold.
- `rules/plan-format.md` (Guardrail 3) is missing from the repo. Its 60s rule still holds as the principle behind the cap.
- `scripts/run-tests.sh` exists, but `grep -n verify` found no verify-row lint step in it. The "L1 verify-row lint" step the records describe may have been removed or moved.
- Both records are 79 and 84 days old (2026-08-17 and 2026-08-12, against 2026-11-04). That is more than 30 days.
- The index says 45 entries and was last updated 2026-10-29. No later record is known.

**Search surface:** docs/solutions/INDEX.md, docs/solutions/critical-patterns.md, docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md, docs/solutions/harness/committed-diff-scoped-lint-skips-uncommitted-work.md. Path checks by `ls`, `find` and `grep` on scripts/, plugins/ and rules/.
