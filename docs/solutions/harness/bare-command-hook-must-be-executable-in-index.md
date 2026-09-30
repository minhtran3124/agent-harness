---
problem_type: bug
module: hooks/registration
tags: hook-registration, file-mode, exit-126, fail-open, bash-invoked-tests, settings-json, deploy-propagation, correctness-review-catch
severity: critical
applicable_when: Adding or replacing a hook that settings.json (or a derived consumer settings.json) registers as a bare command path, i.e. with no `bash` prefix — including any new file created by an editor or agent Write tool, which defaults to 100644.
affects:
  - tests/scripts/settings-wiring.test.sh
  - hooks/commit-gate.sh
supersedes: null
confidence: high
confirmed_at: 2026-09-29
---
## Problem

`hooks/commit-gate.sh` was created by an agent's Write tool and committed with git mode `100644`.
`settings.json` registers it as the bare command `hooks/commit-gate.sh`, and
`scripts/deploy-harness.sh` derives it as `$CLAUDE_PROJECT_DIR/.claude/hooks/commit-gate.sh
--profile <p>`, also with no interpreter. Every hook it replaced had been `100755`.

When it ran, the runtime got `Permission denied` and exit 126. Claude Code treats only exit 2 as a
PreToolUse block, so every `git commit` proceeded with no gate applied: no secrets scan, no
escalation deny, no lane evidence, no risk corroboration. Deploy copies with `cp` and has no
`chmod`, so every consumer install would have inherited the dead gate.

It survived through 13 per-task reviews, a context-propagation audit and a green suite (200+
commit-gate assertions). Correctness-review caught it (`prior-art` and `call-site-impact` angles).

## Root Cause

Two independent facts combined:

1. A new file written by an agent's Write tool (or most editors) is created `0644`. Nothing in the
   workflow set the execute bit.
2. Every hook test invokes the hook as `bash "hooks/$hook"` (`tests/lib.sh` `run_hook` and
   `run_hook_args`). An explicit interpreter does not need the execute bit, so the tests exercised
   a different invocation from the runtime's.
   - The wiring guard (`tests/scripts/settings-wiring.test.sh`) checked that the file exists and
     has a shebang.
   - `scripts/lint-doc-truth.sh` checked `[ -f "$cmd" ]`.

   Both matched the *spelling* of a runnable hook, not the *property* "the runtime can execute
   it".

## Fix

- `git update-index --chmod=+x hooks/commit-gate.sh` (commit `58c6196`; blob unchanged, mode
  `100644` → `100755`).
- The wiring test now asserts, for every command registered in `settings.json`:
  - `[ -x "$cmd" ]`;
  - the index mode is `100755`, via `git ls-files -s -- "$cmd"` (commit `d8688c7`). A local
    `chmod +x` must not mask a committed `100644`, and deploy propagates the tracked mode.

## Regression Test

`bash tests/scripts/settings-wiring.test.sh`, case "every settings.json hook command resolves to
an executable file with a bash shebang".

- Proven non-vacuous: run against a checkout of `7f7c370` it reports `not executable:
  hooks/commit-gate.sh`.
- With the file `chmod +x`'d but the index still `100644`, it reports `tracked mode 100644 (want
  100755)`.
- CI runs the root-settings half of this test on every PR (it does not need `.claude/`).

## Code Example

```bash
# reproduce the fail-open
printf '%s' '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | sh -c 'hooks/commit-gate.sh'
# sh: hooks/commit-gate.sh: Permission denied   (exit 126 — not a block)
```

## Prevention

- Test through the same invocation the runtime uses. For a bare-command hook that means executing
  the path, not `bash path`. A harness helper that always prepends `bash` hides a whole class of
  registration defects.
- When a rename or merge creates a new hook file, check `git diff --summary` for `create mode
  100644 hooks/...` before the first commit.

## Related

- docs/solutions/harness/ratchet-matches-spelling-not-property.md
- docs/solutions/harness/automation-readiness.md
