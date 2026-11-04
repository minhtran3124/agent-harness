Verdict: out-of-date match

**Possibly stale**
- `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md` (confirmed_at 2026-08-17, 79 days old). It matches your symptoms: a pipe splits the row, and a whole-suite command passes the 60s cap. It is out of date because the files its advice needs are missing. `scripts/check_verify_rows.py`, `scripts/verify_summary.py`, `scripts/ci-strict-gate.sh` and `rules/plan-format.md` are not at their `affects` paths. A search under `plugins/` for those names also found nothing. Only `scripts/run-tests.sh` exists, and it has no reference to `check_verify_rows` or `verify_summary`. Treat the rule as unconfirmed against this repo until you find where the strict gate lives now.
- `docs/solutions/harness/committed-diff-scoped-lint-skips-uncommitted-work.md` (confirmed_at 2026-08-12, 84 days old). Its fix commands are `check_verify_rows.py` and `verify_summary.py`, which do not exist. Its claim about the `run-tests.sh` L1 lint scope no longer holds either, because `run-tests.sh` has no such step.
- `docs/solutions/critical-patterns.md` has a short entry for the first record, dated 2026-07-17. It is out of date for the same reason.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`, `docs/solutions/harness/committed-diff-scoped-lint-skips-uncommitted-work.md`. I also searched the repo and `plugins/` for the `affects` file names and grepped `scripts/run-tests.sh`.
