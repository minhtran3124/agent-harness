Verdict: known risk

**Do first.**
- Pick one of two options before dispatch (`docs/solutions/harness/parallel-implementers-share-one-git-index.md`, confirmed_at 2026-09-29, no command in the record):
  - Give each same-wave task its own worktree and merge at the wave boundary.
  - Have each implementer commit only its own paths with `git commit -- <its Files list>`.
- Put the ban on `git reset`, `git commit --amend` and `git stash` in the shared worktree into the implementer brief. If a commit swept foreign files, the implementer must report it and stop (same record).
- If an orphan already exists, recover it this way (same record):
  1. Check that the staged index is byte-identical to the orphaned commit's tree. For each file, compare `git show <sha>:<f> | git hash-object --stdin` with `git rev-parse :<f>`.
  2. Re-commit the staged changes as a normal new commit.
  3. Confirm `git diff <orphan> <new>` is empty.
  4. Record the mixed commit as a deviation.
  5. Do not run the denied reset yourself, and do not rewrite history.

**Avoid.**
- A plain `git commit` in a shared worktree. It records everything anyone staged, so a commit gets another task's files and its message is wrong.
- `git reset --soft HEAD~1` to undo that. A sibling may already have moved `HEAD`, so the reset orphans the sibling's commit and leaves its files staged but uncommitted.
- Running a reset for a subagent after it was denied. That is permission laundering.

**Check before done.**
- Check that each commit holds only its own task's Files list. The record says disjoint Files sets stop content conflicts but not index or `HEAD` races.
- Check that the recovery commit's diff against the orphan is empty and that no commit is left dangling.
- Check that the mixed commit is recorded as a deviation.

**Possibly stale.**
- `docs/solutions/harness/parallel-implementers-share-one-git-index.md`: the `affects` path `skills/subagent-driven-development/implementer-prompt.md` has moved. The file is now `plugins/harness/skills/implement/implementer-prompt.md`. A grep of it found no `git reset`, `--amend`, `stash`, pathspec or `git commit` rule. The record's Guardrail was marked "proposed" and has not been added, so the risk is still open. The record is 34 days old.
- `docs/solutions/harness/wave-boundary-verify-evidence.md` was read but not used. It concerns Verify rows in SUMMARY.md, not this symptom. It also notes that `commit-quality-gate.sh` was merged into `hooks/commit-gate.sh`, so its `affects` path is stale.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/parallel-implementers-share-one-git-index.md`, `docs/solutions/harness/wave-boundary-verify-evidence.md`, `plugins/harness/skills/implement/implementer-prompt.md` (grep only)
