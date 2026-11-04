Verdict: known risk

**Do first**
- Give each same-wave task its own worktree and merge at the wave boundary. This is the record's second prevention option. `plugins/harness/skills/implement/implementer-prompt.md` line 9 already says "Implement this step in your own git worktree". Do not let this run share one worktree. Source: `docs/solutions/harness/parallel-implementers-share-one-git-index.md` (confirmed_at 2026-09-29).
- If tasks must share one worktree, have each implementer commit only its own paths with `git commit -- <its Files list>`. Tell each implementer never to run `git reset`, `git commit --amend` or `git stash`. Source: the same record (confirmed_at 2026-09-29).
- If a commit has already swept foreign files or a reset has orphaned a commit, first check that the staged index matches the orphaned commit's tree. Compare `git show <orphan>:<f> | git hash-object --stdin` with `git rev-parse :<f>` for each file. Then re-commit as a normal new commit, check that `git diff <orphan> <new>` is empty, and record the mixed commit as a deviation. Do not rewrite history. Do not run, from the controller, a reset that the subagent was refused, because that is permission laundering. Source: the same record (confirmed_at 2026-09-29).

**Avoid**
- Do not rely on "stage and commit in separate Bash calls" or "only edit files in your Files list". A plain `git commit` records the whole shared index, so one task's commit swept in the other task's staged files.
- Do not run `git reset --soft HEAD~1` in a shared worktree. A sibling may have moved `HEAD`, so the reset moves `HEAD` off the sibling's commit and leaves it dangling, with its files staged but uncommitted.
- Do not run a denied reset from the controller on the subagent's behalf. It launders a refused permission.

**Check before done**
- Run `git log --stat` on each wave commit. Each commit should touch only its own task's Files list, and no commit message should describe fewer files than the commit holds.
- Run `git fsck --lost-found` or `git reflog`. No dangling commit may hold work that is missing from the branch.
- The guardrail in the record is still only "proposed". `implementer-prompt.md` has no pathspec-commit or no-reset rule, so check by hand that the dispatch brief states it.

**Possibly stale**
- `docs/solutions/harness/parallel-implementers-share-one-git-index.md`: its `affects` path `skills/subagent-driven-development/implementer-prompt.md` is missing. The file now lives at `plugins/harness/skills/implement/implementer-prompt.md`. Its guardrail target `tests/scripts/context-propagation-regression.test.sh` also does not exist, so drop that step of the guardrail. The principle still holds.
- The same record is 36 days old (confirmed_at 2026-09-29, today 2026-11-04), which is over 30 days.
- `docs/solutions/harness/wave-boundary-verify-evidence.md` (confirmed_at 2026-07-23) is out of date and over 30 days old. It names `hooks/commit-quality-gate.sh`, which the record itself marks as merged into `hooks/commit-gate.sh`. It only loosely relates to this task, so I did not list its advice above.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/parallel-implementers-share-one-git-index.md`, `docs/solutions/harness/wave-boundary-verify-evidence.md`, and a grep of `plugins/harness/skills/implement/implementer-prompt.md`. Globs for `**/implementer-prompt.md` and `**/context-propagation-regression.test.sh`.
