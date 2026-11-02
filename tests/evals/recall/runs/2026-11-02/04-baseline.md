Verdict: this is a known failure, and the fix the record proposes never landed in `plugins/`. It's in `docs/solutions/harness/parallel-implementers-share-one-git-index.md`. I treated your message as a report of an incident, or as a recall query, since the same text is eval 4 in `recall/evals/evals.json:72`. I changed no files.

**Cause:** the git index and `HEAD` belong to the worktree, not to each agent. A plain `git commit` records whatever anyone has staged, and `git reset --soft HEAD~1` moves whatever commit is on top by then. Tasks with separate files don't prevent either problem.

**Do first**
1. Stop the agents in that worktree, then compare the orphaned commit with the staged index for each file. `git show <orphan>:<file> | git hash-object --stdin` should equal `git rev-parse :<file>`.
2. If every file matches, commit the staged changes as a normal new commit, and confirm `git diff <orphan> <new>` is empty.
3. Record the mixed commit as a deviation.

**Avoid**
- Don't rewrite history to separate the mixed commit.
- Don't run a reset for a subagent if auto mode denied it, because that bypasses the denial.
- Don't use `git reset`, `git commit --amend` or `git stash` in a shared worktree.

**Check before done**
- Each step runs in its own worktree, as `implement/SKILL.md:19-20` requires, and worktrees merge at the group boundary. If a worktree must be shared, each agent commits with `git commit -- <its files>`.
- `git log --stat` shows that each commit holds only its own task's files.
- The orphaned commit's content is reachable from the branch.

**Possibly stale**
- **Record age:** it was confirmed on 2026-09-29, so it is 34 days old and past the 30-day limit.
- **Target path:** the guardrail targets `skills/subagent-driven-development/implementer-prompt.md`. The glob found no such file, though it may skip hidden directories. The live prompt is `plugins/harness/skills/implement/implementer-prompt.md`, and it has no pathspec-commit or no-reset rule.
- **Regression test:** the proposed `tests/scripts/context-propagation-regression.test.sh` doesn't exist.
- **Prevention today:** the only protection is the per-step worktree instruction in `implement/SKILL.md`. `ship.js:379` gives each ticket its own worktree, so that route avoids the problem, but nothing stops a manual dispatch into a shared worktree.

**This branch:** I found no sign of the incident here. `59c2db3` and `126730c` each touch one file. `50003e0` was replaced by an amend and has the same content as `126730c`, so nothing was lost. The amend did happen, so if siblings share this worktree it is the same risky command.

**Not checked:**
- `git fsck` needed approval, so dangling commits are unknown.
- I didn't check the reflogs of the other worktrees (`plan-556`, `recall-skill/adr`, main).
- The `ls` for `~/.claude/skills/subagent-driven-development` was blocked, and it never reported `.claude/skills` in this repo, so neither location is confirmed.
- If the incident happened elsewhere, I haven't seen it.

**Decision:** the guardrail should go in its own PR, because it's outside #556. That PR should add the rule to the live implementer prompt, add a presence test, and fix the record's `affects` path.

Search surface: `docs/solutions/INDEX.md` and `docs/` (grep), `plugins/harness/skills/implement/`, `plugins/harness/workflows/ship.js`, grep of `plugins/` and `tests/` for pathspec and amend rules, and this worktree's reflog and `git log --stat`.
