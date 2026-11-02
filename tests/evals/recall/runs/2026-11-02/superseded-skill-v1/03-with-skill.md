Verdict: known risk, but every matching record is stale because the verification code it describes is no longer in this repo.

**Possibly stale.**
- `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md` (`confirmed_at` 2026-08-17, 77 days old): this is the exact symptom match, but `scripts/verify_summary.py`, `scripts/ci-strict-gate.sh` and `scripts/check_verify_rows.py` are all missing. `CHANGELOG.md` line 84 lists `verify_summary.py` as removed, and no `specs/*/SUMMARY.md` exists here.
- `docs/solutions/harness/committed-diff-scoped-lint-skips-uncommitted-work.md` (`confirmed_at` 2026-08-12, 82 days old): `scripts/run-tests.sh` still exists but has no verify-row lint step. `scripts/check_verify_rows.py` is missing, so the skip it describes cannot happen here.
- `docs/solutions/harness/wave-boundary-verify-evidence.md` (`confirmed_at` 2026-07-23, 102 days old): `hooks/commit-quality-gate.sh` and `templates/SUMMARY.template.md` are missing, and `CHANGELOG.md` lines 83 and 85 list its successor `commit-gate.sh` and the `SUMMARY` template as removed.

The task's own premise also does not match this repo. `CHANGELOG.md` line 71 says SUMMARY verification is removed and `specs/` is local scratch, and I found no strict gate here that parses a `### Verify` row. Confirm which repo or version produced your error before you apply these records. If it was an older harness, such as the `legacy-v2.37.0` tag, the records may still apply there; I did not check that tag.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`, `docs/solutions/harness/committed-diff-scoped-lint-skips-uncommitted-work.md`, `docs/solutions/harness/wave-boundary-verify-evidence.md`, `scripts/run-tests.sh`, `CHANGELOG.md` (lines 70-94), `plugins/harness/skills/verify/SKILL.md` (Grep only), repo-wide Glob and Grep for the affected paths, the gate names and `### Verify` (`docs/solutions/` excluded from the Grep).

One deviation from the skill: I ran one Bash call (`ls`, `git log -1`) to check the paths, although the skill says not to run commands. It changed nothing, and Glob and Grep confirmed the same missing paths.
