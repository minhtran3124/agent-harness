---
problem_type: bug
module: scripts/install-harness
tags: bash, installer, side-effects, consent-gate, curl-pipe-bash, ordering, child-script-prompt
severity: high
applicable_when: Adding any step to an installer or setup script that changes the machine outside the target (downloads, installs a tool, edits shell profiles, starts a background job) — place it after every point that can still abort, including prompts inside child scripts the installer calls.
affects:
  - scripts/install-harness.sh
supersedes: null
confidence: high
confirmed_at: 2026-10-09
---
## Problem

`install-harness.sh` gained an `ensure_uv` step that downloads and runs the astral.sh uv
installer (which writes `~/.local/bin/uv`, edits `.profile`/`.bashrc`/`.zshrc`) and starts a
detached `uvx code-review-graph` PyPI pre-fetch. It was first placed with the other prerequisite
checks, before source resolution and the existing-harness "Re-sync it? [y/N]" gate. A user who
answered `N` (or a no-tty run without `--yes`, a bad `--source`, a failed clone) got uv installed
anyway, followed by `Aborted (no changes made).` — a false statement.

The first fix moved the call below the installer's own gates and was still wrong:
`deploy-harness.sh`, which the installer runs later, has its own interactive `[k]/[o]/[b]/[a]`
protected-file prompt whose `a` prints "Aborted — nothing written." and exits 1.

## Root Cause

The step was placed by *kind* ("prerequisite / environment setup belongs at the top") rather
than by *effect* ("this mutates the machine, so it belongs after the last abort"). The second
miss came from enumerating abort points only in the file being edited; the abort that remained
lived in a child script invoked by that file.

## Fix

Run `ensure_uv` and the pre-fetch immediately after `bash "$SRC/scripts/deploy-harness.sh" …`
returns 0 (`3b99e4d`), keeping only read-only probes (`command -v jq/git`) in the prerequisite
section. `UVX_MISSING` is still set before both readers (pre-fetch guard, closing banner) on
every path, and `--dry-run` still prints the would-install lines before exiting.

## Regression Test

`tests/scripts/install-harness.test.sh` row "declined re-sync installs nothing": install once
with `CS_NO_UV=1`, then re-run without `--yes`, with no controlling terminal
(`start_new_session=True`), `CS_NO_UV` unset, `uvx` missing and a fake `curl` that logs calls —
asserts rc != 0, "Re-run with --yes" in the output, and no `curl.log`. The deploy-prompt abort
is not covered by a test (it needs a real tty); it is covered by code order and review.

## Prevention

When adding a machine-mutating step, grep the script **and every script it invokes** for
`fail`, `exit 1`, `read -r`, `/dev/tty`, `[y/N]` and place the step after the last hit that can
fire on a normal run. A correctness re-review of the move found the child-script abort that the
first fix missed — re-review the fix, not only the original diff.

## Related

- docs/solutions/scripts/test-r-dev-tty-does-not-detect-missing-controlling-terminal.md
