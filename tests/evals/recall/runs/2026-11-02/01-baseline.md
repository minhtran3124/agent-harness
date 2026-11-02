**Your hook script almost certainly doesn't have its execute bit set.** A bare path makes the shell run the file directly, which needs that bit. New files from editors or an agent's Write tool usually come out as `0644`, so the shell returns `Permission denied` and exit 126. I haven't confirmed this on your file, because I couldn't find the hook.

## Fix
Run this from the repo root, replacing `path/to/hook.sh` with your path:

```bash
chmod +x path/to/hook.sh                      # makes it work now
git update-index --chmod=+x path/to/hook.sh   # if tracked: records 100755 in git
```

Do both if the file is tracked. With `chmod` alone, your machine works but git may not record the change, so anyone else who checks it out or installs it can hit the same error.

To check the result:

```bash
git ls-files -s -- path/to/hook.sh            # should start with 100755
sh -c 'path/to/hook.sh' </dev/null; echo $?   # should not be 126
```

If the script reads JSON from stdin, it may exit with another error on the empty input. That's fine, as long as it isn't 126.

The script also needs a valid shebang, such as `#!/usr/bin/env bash`. If the mode is already `100755` and you still get 126, check whether the file is on a `noexec` mount, or whether the path points to a directory.

Alternatively, register it as `bash path/to/hook.sh`, which doesn't need the execute bit. All the hooks in your global settings and `plugins/harness/hooks/hooks.json` run through `bash`, but keeping a bare path is fine once the mode is right.

## Your hook may not have been running
**If this hook is a gate, it hasn't been blocking anything.** Claude Code only treats exit 2 as a block, so exit 126 lets the tool call go ahead. The same thing once disabled `hooks/commit-gate.sh`: every `git commit` went through with no gate. That case is written up in `docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md`.

Tests can hide this too. A test that runs `bash hooks/x.sh` passes without the execute bit, so also run the hook by its path, as in the check above.

## What I checked
- **Your hook:** I didn't find a bare-path hook in `~/.claude/settings*.json`, and the repo's own `settings.json` has no `hooks` key. This worktree has no `.claude/` directory, so the registration is probably in another project's settings. I can't say which file is affected.
- **The solution entry:** it's 34 days old and `hooks/commit-gate.sh` no longer exists, since hooks now live in `plugins/harness/hooks/`. The cause still applies, and `tests/scripts/settings-wiring.test.sh:27-28` still checks for mode `100755`.
- **Limit of that test:** based on the lines I read, it checks registered hooks, including the plugin's. A hook in another project's settings probably won't be covered.
