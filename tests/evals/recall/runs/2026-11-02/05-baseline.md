**I couldn't find anything in the harness that denies a commit because of untracked Python files, and I couldn't reproduce the denial.** Nothing has been changed. The conclusions below come from reading the code. My throwaway-repo test needed approval I didn't have, so the hooks were never actually run.

**Hooks I ruled out for this condition:**
- **`secrets-scan.sh`:** it only reads staged content (`git diff --cached`, lines 10 and 14), so it can't see untracked files and has no `.py` logic. The installed 5.3.1 copy reads the same on inspection.
- **`merge-guard.sh`:** a keyword search found only `--match-head-commit` handling for merges. I didn't read the whole script.
- **Orca hook:** the only PreToolUse hook in the part of `~/.claude/settings.json` I read (lines 1–113 of 268). `claude-hook.sh` has no `deny`, `permissionDecision`, `exit 2` or `.py` matches.
- **`hookify`:** it has a PreToolUse hook, but it isn't in `enabledPlugins`.
- **`security-guidance`:** it does track untracked files, but it reviews commits in PostToolUse and isn't in `enabledPlugins` either.

**Likely causes:**
1. **Permission prompt rather than a hook (my best guess):** this session hit the same kind of denial on compound commands: "This Bash command contains multiple operations. The following parts require approval". A `git add && git commit` could get the same response, and the untracked files would just be a coincidence.
2. **A secret already staged:** `secrets-scan.sh` runs before `git add` does, so it blocks on whatever was staged earlier. A staged Python file containing something like `password = "..."` would block the commit, and that could look like a Python file problem.

**Not checked:**
- The two plugin directories in `CLAUDE_CODE_PLUGIN_DIRS` (`cc-ste-mod`, `claude-code-tokscope/mod`).
- Hooks declared anywhere other than `hooks/hooks.json`.
- Lines 114–268 of your user settings.
- This worktree has no untracked `.py` files, only `.md` files under `tests/evals/recall/`, so your denial happened in a different state from this one.

**Separate bug in `secrets-scan.sh`:** in a combined `git add x.py && git commit`, the scan runs before `x.py` is staged. A secret in a newly added file therefore passes unscanned, which is the opposite of what you reported. Running `git add` and `git commit` as separate Bash calls avoids this, and also avoids the staging-order confusion in cause 2.

To pin this down, I need the exact denial text. `BLOCKED: potential secret…` means cause 2, `multiple operations` means cause 1, and anything else points to one of the unchecked sources.
