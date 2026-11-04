Verdict: known risk

**Do first**
- Give each same-wave implementer its own worktree and merge at the wave boundary. If that is not possible, tell each one to commit only its own files with `git commit -- <its Files list>`. They must never run `git reset`, `git commit --amend` or `git stash` in a shared worktree. Source: docs/solutions/harness/parallel-implementers-share-one-git-index.md (confirmed_at 2026-09-29).
- If a commit has already taken a sibling's files, do not run a reset. Check that the staged index matches the orphaned commit's tree: `git show <sha>:<f> | git hash-object --stdin` against `git rev-parse :<f>` for each file. Then re-commit the staged changes as a normal new commit and confirm `git diff <orphan> <new>` is empty. Record the mixed commit as a deviation. Same record (confirmed_at 2026-09-29).
- Add the guardrail rule to the implementer prompt. The record only proposes it. Same record (confirmed_at 2026-09-29).

**Avoid**
- A plain `git commit` in a shared worktree. It records the whole index, so it commits sibling tasks' staged files into a commit whose message describes only your task.
- `git reset --soft HEAD~1` to undo that commit. A sibling may have committed on top, so the reset moves `HEAD` off the sibling's commit. That commit is orphaned and its files are left staged but not committed.
- Running a reset that auto mode refused, on the subagent's behalf. This is permission laundering. Verify the index and re-commit instead.

**Check before done**
- Each commit in the wave holds only that task's Files list. Confirm with `git show --stat` on every commit.
- No commit in the wave is orphaned or dangling, and the index is clean after the last task.
- The prompt's pathspec-commit rule has a presence case in `tests/scripts/context-propagation-regression.test.sh`, so the rule cannot silently drop out. The record lists this as part of the proposed guardrail. I did not check that file or its test.

**Possibly stale**
- docs/solutions/harness/parallel-implementers-share-one-git-index.md is not out of date. It is 36 days old (confirmed_at 2026-09-29, today 2026-11-04), which is more than 30 days.
- Its `affects` path `skills/subagent-driven-development/implementer-prompt.md` no longer exists. The file is now at `plugins/harness/skills/implement/implementer-prompt.md`. A search of that file for `git commit`, `git reset`, `amend` and `stash` found no match. So the proposed guardrail is not yet in the prompt, and the advice still applies.

**Search surface:** docs/solutions/INDEX.md, docs/solutions/critical-patterns.md, docs/solutions/harness/parallel-implementers-share-one-git-index.md, plugins/harness/skills/implement/implementer-prompt.md (grepped only)
