The cause is a known bug in this repo, and I haven't changed anything because **your script isn't in this checkout**. I searched `plugins/harness` and `scripts/` for self-locating code. Nothing the plugin ships uses its own location to find the project.

Don't ask git for the root from the script's own directory. `claude plugin marketplace add` clones, so the installed copy sits inside a git repo. `git -C "$SCRIPT_DIR" rev-parse --show-toplevel` therefore exits 0 and returns that clone, not your project, so nothing fails. This is recorded in `docs/solutions/harness/hook-root-must-not-come-from-install-location.md`.

## The fix
```bash
ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -z "$ROOT" ] && { echo "cannot determine the project root, refusing to guess" >&2; exit 2; }
```

- **Order:** `CLAUDE_PROJECT_DIR` comes first and still works if a compound command changed the working directory. Git run from the working directory is the fallback.
- **No fallback to the script's location:** don't keep `dirname "$0"`, `BASH_SOURCE` or `__file__` as a source for the root, even as the last option. A plausible wrong answer is worse than a failure.
- **Keep self-location for the plugin's own files only:** templates and libraries are fine. `init-structure.sh:14` and `old-install.sh:27` do this correctly.
- **Python:** `plugins/harness/scripts/rebuild_solution_index.py:63` shows a similar approach, using `--root` with the working directory as the default. Its comment gives the same reason. It doesn't read `CLAUDE_PROJECT_DIR`, so copy the order above if your script might not start in the project.
- **Skills:** pass the root in explicitly, as `setup` does with `--root ${CLAUDE_PROJECT_DIR}` (`plugins/harness/skills/setup/SKILL.md:13`).
- **Non-blocking scripts:** if your script is a hook that shouldn't block work, warn and exit 0 instead of `exit 2`.

## Check the fix
1. Put the script inside a different git repo, and set the working directory to your project.
2. Run it with `CLAUDE_PROJECT_DIR` unset, and confirm it acts on your project.
3. Check any edits the script already made to the plugin clone, because those landed in the wrong repo.

## What I couldn't confirm
- **The record is partly out of date:** it was last confirmed on 2026-09-09, more than 30 days ago, and several hooks it names have since been merged or removed.
- **Regression test:** the test it cites, `tests/hooks/repo-root-resolution.test.sh`, doesn't exist here, so the manual check above stands in for it. `scripts/check-hook-root-source.sh` does exist, but I didn't read what it scans, and the record warns that it can miss other spellings of the same bug.
- **Your cache:** I wasn't allowed to list `~/.claude/plugins/cache`, so I haven't seen the installed copy.
- **`CLAUDE_PROJECT_DIR` in the Bash tool:** my check of this needed approval and didn't run. If the variable is unset there, the git fallback only gives the right root when the script runs from inside your project.
