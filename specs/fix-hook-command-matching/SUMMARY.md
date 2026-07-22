<!--
  Canonical SUMMARY.md shape. Header block is machine-read by
  hooks/risk-corroboration.sh (Lane) and the trust-metrics ledger.
-->

# fix-hook-command-matching — Summary

Lane: high-risk
Confidence: high
Reason: Hard gate — changes .claude/hooks/* (commit-quality-gate, risk-corroboration, branch-guard, check-untracked-py) and settings.json (high-blast files); also flags 8 (existing hook behavior) + 9 (no bypass tests exist).
Flags: existing-behavior, weak-proof
Affects: hooks/commit-quality-gate.sh, hooks/risk-corroboration.sh, hooks/branch-guard.sh, hooks/check-untracked-py.sh, settings.json (+ .claude/ deployed copies)
Input-type: harness improvement

> `Lane` drives ceremony; `Confidence` drives interruption. Hard gate forces high-risk;
> confidence is high (bug reproduced live in research), so work proceeds autonomously.

### Intent

Wave 0a của harness v0.3 (docs/harness-v03-plan-overview.md): fix command-matching bypass trong các commit-gate hook. Cụ thể: hooks/commit-quality-gate.sh, hooks/risk-corroboration.sh, hooks/branch-guard.sh filter bằng grep -qE '^git commit' nên bypass được bằng 'cd x && git commit', 'git -C dir commit', 'git -c k=v commit', 'command git commit', 'echo done; git commit' (đã chứng minh live trong docs/research/harness-review-improvements/2026-07-03-deep-review-harness-trustworthiness.md DR-1); hooks/check-untracked-py.sh substring match cũng thua 'git -C'. Kèm theo: bỏ field '"if"' và 'statusMessage' không thuộc schema hooks trong settings.json. Thêm regression test cho từng bypass form. Đây là thay đổi hooks/* + settings.json = high-blast Rule 4.

## What changed

Added a shared tokenizing matcher `hooks/lib/git-command.sh` (`hook_cmd_is_git_commit` /
`hook_cmd_is_git_commit_or_push`) and rewired all four commit-gate hooks
(`commit-quality-gate`, `risk-corroboration`, `branch-guard`, `check-untracked-py`) to use it
in place of the `^git commit` anchor / substring match. Removed the four `"if"` permission-rule
filters from `settings.json`. The matcher splits the command on shell separators, skips prefix
tokens (`cd`, env-assignments, `command`/`sudo`/`env`) and git global options (`-C`/`-c`/`-…`),
then exact-matches the subcommand — so every DR-1 bypass (`cd x && git commit`, `git -C d
commit`, `git -c k=v commit`, `command git commit`, `echo done; git commit`) is now gated, while
`echo "git commit"`, `git log --grep=commit`, and `git commit-graph write` are correctly ignored.

### Rationale

The four commit-gate hooks anchor their command filter with `grep -qE '^git commit'` (or a
substring match), so any prefixed/wrapped git invocation slips past the secrets scan, debug
check, pytest gate, and lane corroboration. A shared, tokenizing matcher that recognizes a
`git … commit` invocation regardless of leading `cd`/`&&`/`;`/`|`, `-C`, `-c`, or `command`
closes the class of bypasses. The `"if"` / `statusMessage` keys in settings.json are not part
of the Claude Code hooks schema and are silently ignored — removing them ends the false
impression of config-level gating.

### Alternatives considered

- Match `git` anywhere in the command string (substring) — rejected: too coarse, false-fires
  on `git log`, commit messages containing "git commit", etc.
- Per-hook bespoke fixes — rejected: duplicates the parsing bug four times; a shared helper in
  a sourced lib is the single-source fix and is testable once.

### Deviations

- Rule 3 — Updated `new_repo()` in `tests/lib.sh` to copy `hooks/lib/` into the hermetic test
  repo; without it the rewired hooks fail to source the shared matcher. Test-infra fix required
  to run the changed hooks. (outside PLAN `<files>` — flagged by blast-radius.)
- Correction to intake premise — the deep-review claim (DR-5) that `"if"` and `"statusMessage"`
  are schema-invalid/ignored is WRONG. Official docs (code.claude.com/docs/en/hooks.md) confirm
  both are valid: `if` is a permission-rule filter that gates hook execution; `statusMessage` is
  spinner text. Consequence: removing `"if"` is REQUIRED (not cosmetic) — `if: "Bash(git commit
  *)"` prevented the hooks from firing on wrapped forms like `cd x && git commit`, so the internal
  matcher alone would not have closed the bypass at runtime. `"statusMessage"` was KEPT (valid,
  useful). Source research doc DR-5 should be corrected on this point.

### Verify

<!-- Filled after implementation; each row is a check actually run. -->

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| harness test suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN — 102 py passed, all hook suites pass |
| bypass regression (unit) | `bash tests/hooks/command-matching.test.sh` | 0 | 33 passed — every DR-1 form matched, quoted-separator + false-fire guards |
| wired end-to-end (integration) | `bash tests/hooks/gate-integration.test.sh` | 0 | 8 passed — wrapped commits reach gate; missing-lib fails closed |
| bypass closed (matcher) | `bash -c 'source hooks/lib/git-command.sh && hook_cmd_is_git_commit "cd x && git commit"'` | 0 | exit 0 = wrapped commit now detected (DR-1 form) |

### Rollback

- Revert the PR: `git revert <merge-sha>` (hooks are pure scripts, no persisted state).
- Per-file: `git checkout HEAD~1 -- hooks/commit-quality-gate.sh hooks/risk-corroboration.sh hooks/branch-guard.sh hooks/check-untracked-py.sh settings.json`
- Redeploy old hooks into `.claude/`: `bash scripts/deploy-harness.sh` (or restore from `.harness-backup-*`).

### Review outcomes

- **correctness-review** (Opus reviewer) — found F1 (MODERATE: separators inside quoted strings
  forged a match → net-new false-positive for the 3 anchor hooks) and F2 (LOW: fail-open if the
  matcher lib is missing). Both FIXED: F1 by stripping quoted spans before splitting (real commit
  messages still match); F2 by a `command -v` guard that fails closed (exit 2) on the blocking
  hooks and stays non-blocking (exit 0) on warn-only branch-guard. Exotic false-negatives
  (`(git commit)`, `/usr/bin/git commit`, `sh -c '…'`) documented as known-uncaught in the lib
  header (out of declared scope: no full shell parsing).
- **intent-review** (independent model) — diff satisfies intent; one residual **drift** for human
  sign-off: `statusMessage` was KEPT (intent said remove it) because it is a valid, documented,
  useful key — see Deviations. No gaps, no excess.

### Harness-Delta

- backlog — this whole class of bug (four hooks sharing one broken matcher) is a case for a
  shared, tested hook-input parsing lib; candidate for /compound after v0.3.
