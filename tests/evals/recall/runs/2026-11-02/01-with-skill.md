Verdict: known risk

**Avoid.**
- Registering a hook in settings.json as a bare path (no `bash` prefix) while its file is git mode `100644`. The runtime gets `Permission denied` and exit 126. Claude Code treats only exit 2 as a block, so the hook fails open: the gate silently does nothing. Record: `docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md`.
- Creating the hook file with an agent Write tool or an editor and assuming it is runnable. Those tools default to `0644`, and deploy copies with `cp` and no `chmod`. Every consumer install inherits the non-executable file.
- Trusting green tests as proof the hook runs. Every hook test runs `bash hooks/x.sh`, which ignores the execute bit, so 200+ assertions passed over a dead hook.

**Check before done.**
- Run `bash tests/scripts/settings-wiring.test.sh`. The case "every settings.json hook command resolves to an executable file with a bash shebang" checks `-x` and index mode `100755` for every registered command.
- Look at `git ls-files -s -- <hook path>` for `100755`. A local `chmod +x` can hide a committed `100644`. Fix it with `git update-index --chmod=+x <hook path>`.
- Reproduce the failure by executing the path directly, not through `bash`. For example `printf '%s' '<json>' | sh -c '<hook path>'` prints `Permission denied` with exit 126. Also run `git diff --summary` and look for `create mode 100644 hooks/...`.

**Possibly stale.**
- `docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md` was confirmed 2026-09-29, which is 34 days before today (2026-11-02), so it is over the 30-day mark.
- Its `affects` path `hooks/commit-gate.sh` is not in this worktree. `hooks/` does not exist at the repo root, and no file matching `*commit-gate*` exists anywhere. The only hooks under `plugins/harness/hooks/` are `clean-worktrees.sh`, `hooks.json`, `merge-guard.sh`, `pr-opened.sh`, `secrets-scan.sh` and `session-rules.sh`.
- The other `affects` path, `tests/scripts/settings-wiring.test.sh`, exists.
- The record's premise (bare-command registration, mode 100644, exit 126) still applies to any hook registered this way. I did not check whether the plugin layout, where hooks are registered through `plugins/harness/hooks/hooks.json`, still uses bare paths. Treat the `commit-gate.sh` specifics as historical.

**Search surface:** `/home/minhtran/Documents/minh.tran/projects/.ship-agent-harness/recall-brief/t556/docs/solutions/INDEX.md`, `/home/minhtran/Documents/minh.tran/projects/.ship-agent-harness/recall-brief/t556/docs/solutions/critical-patterns.md`, `/home/minhtran/Documents/minh.tran/projects/.ship-agent-harness/recall-brief/t556/docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md`. I also ran a Glob for `**/settings-wiring.test.sh`, a Glob for `**/commit-gate.sh` and `**/*commit-gate*`, and listed `hooks/` and `plugins/harness/hooks/`.
