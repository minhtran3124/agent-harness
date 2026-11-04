Verdict: known risk

**Do first**
- Check the hook's git index mode, not just the working-tree mode. Run `git ls-files -s -- <hook path>`. If it shows `100644`, run `git update-index --chmod=+x <hook path>`. Then confirm the mode is `100755` in the diff. A local `chmod +x` alone doesn't fix deploys, because they copy the tracked mode. The record explains that a bare-command hook without the execute bit gives `Permission denied` and exit 126. Source: docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md (confirmed_at 2026-09-29).
- Reproduce the failure the way the runtime runs it: execute the path directly, for example `sh -c '<hook path>'`. Don't use `bash <path>`, because that ignores the execute bit. Same record (2026-09-29).
- Alternative that avoids the problem: register the hook with an explicit interpreter instead of a bare path. This repo's `plugins/harness/hooks/hooks.json` already uses exec form with `command: "bash"` and `args: ["${CLAUDE_PLUGIN_ROOT}/hooks/<script>"]`. That form needs no execute bit. This comes from the current wiring test, not from the record's own advice.

**Avoid**
- Don't test the hook with `bash hooks/x.sh`. It passes while the real bare-path run fails with exit 126.
- Don't treat exit 126 as a block. Claude Code blocks only on exit 2, so the hook fails open and its gate silently does nothing.
- Don't create hook files with an editor or the agent Write tool and commit without checking the mode. They default to `100644`.

**Check before done**
- Run `bash tests/scripts/settings-wiring.test.sh`. It asserts that each registered script exists, has a shebang, and is `100755` in the index.
- Run `git diff --summary` and look for `create mode 100644 ...hooks/...` before the first commit.
- Run the hook through its registered form and confirm it gives exit 0 or a deliberate exit 2, not 126.

**Possibly stale**
- The record's `affects` path `hooks/commit-gate.sh` is missing. No `commit-gate*` file exists anywhere in the repo. The hooks now live in `plugins/harness/hooks/` (clean-worktrees, merge-guard, pr-opened, secrets-scan, session-rules). critical-patterns.md notes that risk-corroboration was merged into commit-gate by specs/simplify-hook-surface.
- The record's regression-test wording is partly out of date. `tests/scripts/settings-wiring.test.sh` still exists, but it now checks `plugins/harness/hooks/hooks.json` exec-form hooks rather than bare `settings.json` commands. The repo's own `settings.json` is now asserted to wire no hooks. The index-mode `100755` check still exists. The record's `$CLAUDE_PROJECT_DIR/.claude/hooks/... --profile` deploy derivation was not checked and may be gone.
- The principle still holds: any bare-path command registration needs the execute bit in the index. The commands and file names in the record do not hold.
- The record is 36 days old (2026-09-29 vs 2026-11-04), which is more than 30 days.

**Search surface:** docs/solutions/INDEX.md, docs/solutions/critical-patterns.md, docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md, tests/scripts/settings-wiring.test.sh (lines 1-32), plugins/harness/hooks/ (directory listing)
