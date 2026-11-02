Verdict: known risk

**Avoid.**
- Do not put `git add` and `git commit` in one Bash call while untracked `.py` files exist. The record is `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md`. The PreToolUse hook checks the command string before anything runs. It sees `git commit` plus untracked `.py` files and denies the whole call. The `git add` never runs, so staging stays empty. This happened twice in one session.

**Check before done.**
- Run `git add` in its own Bash call first. Then run `git commit` in a second call, so the hook re-checks against a clean untracked set.
- Before you commit, confirm no untracked `.py` files remain. Stage them, or deliberately leave them out of the commit.
- The record says the deny is correct behaviour. Do not edit the hook to get around it. A `hooks/*` change counts as high-blast.

**Possibly stale.**
- `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md` is 121 days old (`confirmed_at` 2026-07-04).
- Its `affects` path, `hooks/check-untracked-py.sh`, does not exist in this worktree.
- The record's own footer says the script was merged into `hooks/commit-gate.sh` (specs/simplify-hook-surface, 2026-09-29).
- `hooks/commit-gate.sh` is also absent here. A repo-wide search for `commit-gate*`, `check-untracked*` and the deny text `Untracked .py` found only the record itself.
- The `CLAUDE.md` Gotchas note that the record cites is not in this tree either. A grep of `CLAUDE.md` for "untracked" returned nothing.
- The deny text and the current hook behaviour are therefore not confirmed here. This tree may not carry the hook. The split-call workaround is still cheap and safe to follow.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md`. I also searched the worktree for `commit-gate*`, `check-untracked*`, "Untracked .py", and "untracked" in `CLAUDE.md`.
