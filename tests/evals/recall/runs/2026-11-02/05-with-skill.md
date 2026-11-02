Verdict: known risk, but the matching record is stale: no hook in this repo still contains the untracked `.py` deny.

**Possibly stale.**
- `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md` (`confirmed_at` 2026-07-04, 121 days old). This is the exact symptom match, and its advice is to split `git add` and `git commit` into two Bash calls.
  - **Missing path:** its `affects` path `hooks/check-untracked-py.sh` no longer exists. That hook merged into `commit-gate.sh`, which `CHANGELOG.md:83` lists as removed.
  - **Premise mismatch:** the only PreToolUse Bash hooks in `plugins/harness/hooks/hooks.json` are `secrets-scan.sh` and `merge-guard.sh`. Neither contains the words `untracked`, `ls-files`, `.py` or `not staged`.
  - **Rule gone from CLAUDE.md:** the "split into two Bash calls" rule the record cites is no longer there. Nothing in `CLAUDE.md` matches `git add`, and the only `git commit` match is the `secrets-scan.sh` table row.
  - **Implication:** a deny with this symptom now comes from outside this repo's hooks, such as an older deployed copy in `.claude/hooks/`. Read the deny message and find which hook sent it. I did not inspect any deployed copies.
- `docs/solutions/harness/parallel-implementers-share-one-git-index.md` (`confirmed_at` 2026-09-29, 34 days old). Its `affects` path `skills/subagent-driven-development/implementer-prompt.md` is missing; the nearest file is `plugins/harness/skills/implement/implementer-prompt.md`. It only touches the "add and commit in separate Bash calls" brief. Its topic is the shared git index in parallel waves, not this deny.
- `docs/solutions/harness/test-and-doc-lint-gate-scope.md` (`confirmed_at` 2026-07-17, 108 days old). Its premise is false: `scripts/run-tests.sh:119` now builds `PYTESTS` with `find`, not an explicit list. It is only loosely related, through the untracked Python files.

**Search surface:** docs/solutions/INDEX.md, docs/solutions/critical-patterns.md, docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md, docs/solutions/harness/parallel-implementers-share-one-git-index.md, docs/solutions/harness/test-and-doc-lint-gate-scope.md, plugins/harness/hooks/hooks.json, plugins/harness/hooks/ (Grep), CLAUDE.md (Grep), CHANGELOG.md (lines 70-84, 170-183), scripts/run-tests.sh (Grep)
