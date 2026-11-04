Verdict: known risk

**Do first**
- Make the hook file executable in git: `git update-index --chmod=+x <hook path>` (docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md, confirmed_at 2026-09-29). The record's cause is the same as yours: the file was created at mode `100644` and registered with no interpreter, so the runtime got "Permission denied" and exit 126.
- Check the mode that git holds, not only the local file. Run `git ls-files -s -- <hook path>` and expect `100755`. A local `chmod +x` can hide a committed `100644`, and deploy copies the tracked mode (same record, confirmed_at 2026-09-29).
- Test the hook the way the runtime runs it: execute the path directly, for example `printf '%s' '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | sh -c '<hook path>'`. If you only run `bash <hook path>`, the test passes even when the execute bit is missing (same record, confirmed_at 2026-09-29).

**Avoid**
- Treating exit 126 as a block. Claude Code blocks a PreToolUse hook only on exit 2. With exit 126 the action goes ahead and the gate is silently skipped.
- Testing with `bash hooks/x.sh`. It ignores the execute bit, so a green suite hid this defect through 13 task reviews and 200+ assertions.
- Fixing only your local copy. `scripts/deploy-harness.sh` copies with `cp` and has no `chmod`, so every consumer install inherits the mode that is committed.

**Check before done**
- Run `bash tests/scripts/settings-wiring.test.sh`. Its case "every settings.json hook command resolves to an executable file with a bash shebang" checks `-x` and index mode `100755` for every registered command.
- Run `git diff --summary` and look for `create mode 100644 hooks/...` before you commit a new hook.

**Possibly stale**
- docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md is 36 days old (confirmed_at 2026-09-29, today 2026-11-04), which is over 30 days. Its `affects` path `hooks/commit-gate.sh` is not found anywhere in the repo. `tests/scripts/settings-wiring.test.sh` does exist. The index notes that `risk-corroboration.sh` was merged into `hooks/commit-gate.sh` in specs/simplify-hook-surface, so the hook may have been renamed or moved. The advice does not depend on that file, so it still holds.

**Search surface:** docs/solutions/INDEX.md, docs/solutions/critical-patterns.md, docs/solutions/harness/bare-command-hook-must-be-executable-in-index.md, Glob tests/scripts/settings-wiring.test.sh (found), Glob **/hooks/commit-gate.sh (not found), Glob **/commit-gate.sh (not found)
