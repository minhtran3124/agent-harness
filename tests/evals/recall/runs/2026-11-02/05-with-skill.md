Verdict: known risk. The combined `git add` and `git commit` denial is recorded, but its hook script is no longer in the repo.

**Do first**
- Run `git add <files>` in one Bash call. Run `git commit -m "..."` in a second call. A PreToolUse hook checks the whole command string and the repo state before any part of it runs. The untracked `.py` files are therefore still untracked when the combined call is checked, and the `git add` never runs. Source: `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md` (confirmed_at 2026-07-04). The record gives no command beyond the two split calls.

**Avoid**
- Do not write `git add a.py && git commit -m ...` as one call while untracked `.py` files exist. The whole call is denied with "Untracked .py not staged (would break CI imports)". Nothing is staged. The record says this happened twice in one session.

**Check before done**
- After the `git add` call, confirm `git status` shows no untracked `.py` files you meant to commit. The commit call is checked against the repo state at that moment.

**Possibly stale**
- The record is 123 days old (confirmed_at 2026-07-04, today is 2026-11-04). That is more than 30 days.
- The `affects` path `hooks/check-untracked-py.sh` is missing. My Glob for `**/check-untracked-py.sh` found nothing. The record itself says it was merged into `hooks/commit-gate.sh`, and a Glob for `**/commit-gate.sh` also found nothing.
- The record says `CLAUDE.md` Gotchas holds the "split into two Bash calls" rule. A Grep over the repo, excluding `docs/solutions/`, found no such text in `CLAUDE.md`. That pointer is out of date.
- I could not confirm that any current hook still produces the "Untracked .py" deny. The split-call advice names no missing file or command, so I kept it. The reason: any PreToolUse hook that reads the command string would behave the same way.

**Search surface:** `docs/solutions/INDEX.md`, `docs/solutions/critical-patterns.md`, `docs/solutions/harness/pretooluse-hook-denies-combined-git-add-commit.md`. I also ran a Glob for `**/check-untracked-py.sh`, a Glob for `**/commit-gate.sh`, and a Grep for "Untracked .py" and "split…two Bash" outside `docs/solutions/`.
