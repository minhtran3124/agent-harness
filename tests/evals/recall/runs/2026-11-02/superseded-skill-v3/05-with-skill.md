Verdict: out-of-date match

**Possibly stale**
- `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md` (confirmed_at 2026-07-04, about 123 days old, over the 30-day limit). It is out of date for two reasons:
  - It says it is superseded. Its last line reads "Superseded by specs/simplify-hook-surface (2026-09-29): check-untracked-py.sh merged into hooks/commit-gate.sh".
  - Neither `check-untracked-py.sh` nor `commit-gate.sh` exists anywhere in this worktree. `plugins/harness/hooks/` holds only `clean-worktrees.sh`, `hooks.json`, `merge-guard.sh`, `pr-opened.sh`, `secrets-scan.sh` and `session-rules.sh`. A search of `plugins/harness` for "untracked" found no hook that implements the rule.
  - The record's CLAUDE.md note ("split into two Bash calls") was not found either. The `CLAUDE.md` search returned no matches.
- Nothing in the record can be applied to the current hook surface without first re-checking the live hook.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md`. I also ran Glob and Grep over the worktree and `plugins/harness/` for `check-untracked-py.sh`, `commit-gate.sh` and "untracked".
