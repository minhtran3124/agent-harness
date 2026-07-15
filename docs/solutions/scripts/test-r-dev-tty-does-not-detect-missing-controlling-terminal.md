---
problem_type: bug
module: scripts/deploy-harness
tags: bash, dev-tty, controlling-terminal, curl-pipe-bash, harness-scripts, ci-macos-ubuntu, narrow-guard
severity: critical
applicable_when: Watch for this when a shell script decides whether it may prompt the user — `[ -r /dev/tty ]`, `[ -t 0 ]`, and `[ -t 1 ]` are all wrong, and the failure is silent.
affects:
  - scripts/deploy-harness.sh
  - scripts/install-harness.sh
supersedes: null
confidence: high
confirmed_at: 2026-07-10
---
## Problem

A tty-less CI re-sync of the harness (`curl … | bash`, no `--yes`) printed an interactive conflict menu to stdout that nothing could answer. It happened to land on the safe `POLICY=keep`, but the intended `⚠ … keeping your local copy; incoming saved as <file>.harness-incoming` warning (`scripts/deploy-harness.sh:148-149`) never printed. A conflict was resolved silently, with no operator-visible signal.

## Root Cause

The guard was `[ -r /dev/tty ]`. That is an `access(2)` mode-bit check on the `/dev/tty` **alias device node**. Those bits stay world-readable even in a process with no controlling terminal, so the test returns true after `setsid()`.

It answers *"is this node readable"*, not *"can I open my controlling terminal"*. The real `open(2)` fails with `ENXIO`.

So `elif [ "$YES" -eq 1 ] || [ ! -r /dev/tty ]; then POLICY=keep` was **dead code**. Control fell through to the interactive `else` branch, and `read -r ans < /dev/tty || true` swallowed the `ENXIO`, leaving `$ans` empty — which fell to the `*)` case, `POLICY=keep`.

The outcome was correct **by accident of a second guard**, not by the documented condition. That is what made it invisible: the tests passed, the behavior was safe, and the branch that was supposed to run never did.

## Fix

`scripts/deploy-harness.sh` (commit `ac7f472`):

```bash
# True only when this process can actually open its controlling terminal.
have_tty() { (exec < /dev/tty) 2>/dev/null; }
```

used as `elif [ "$YES" -eq 1 ] || ! have_tty; then`. Opening it in a subshell is the only honest test, and the subshell means the caller's stdin is untouched.

`scripts/install-harness.sh:122` still carries the same `[ -r /dev/tty ]` idiom. It was left alone: its failure mode is benign (empty reply → `fail "Aborted (no changes made)"`, which is the documented "re-run with `--yes`" behavior) and it is outside the change's scope per `rules/behavior.md` §3.

## Regression Test

`tests/scripts/resync-conflict.test.sh` case 4 forces a genuinely ctty-less process (`subprocess.run(..., start_new_session=True)` → `setsid`), runs deploy with no `--yes`, and asserts the output contains `keeping your local copy`.

Mutation-verified: reverting `have_tty()` to `[ -r /dev/tty ]` fails **exactly that one assertion** and no other. Without the warning assertion, the mutant survives — which is why the assertion, not the pass count, is the guard.

## Code Example

The probe that proves the mechanism — same process, opposite answers:

```python
import os, subprocess
pid = os.fork()
if pid == 0:
    os.setsid()                     # sever the controlling terminal
    subprocess.run(['/bin/sh','-c',
      'if [ -r /dev/tty ]; then echo "test -r  -> READABLE"; else echo "test -r  -> no"; fi;'
      'if read x < /dev/tty 2>/dev/null; then echo "read     -> ok"; else echo "read     -> FAILED"; fi'])
    os._exit(0)
os.waitpid(pid, 0)
```

```
test -r  -> READABLE
read     -> FAILED        # /dev/tty: Device not configured (ENXIO)
```

## Prevention

Never use any of these to decide "can I prompt":

| Test | What it actually reports |
|---|---|
| `[ -r /dev/tty ]` | mode bits of the alias node — true with no ctty |
| `[ -t 0 ]` | stdin is a tty — but under `curl \| bash`, stdin **is the script text** |
| `[ -t 1 ]` | stdout is a tty — describes where output goes, not where input comes from |

The only correct test is to attempt the open: `(exec < /dev/tty) 2>/dev/null`.

Also: when a fallback branch is "safe by accident" because a later `|| true` swallows the error, the branch is untested and its user-visible messaging is missing. Assert the *message*, not just the outcome.

## Related

- `docs/solutions/scripts/bash-empty-array-and-jsonl-parsing-gotchas.md` — same class of defect: a guard that handles the one failure mode that was tested, not the mechanism's full failure space.
- `docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md` — how this bug's regression test was proven non-vacuous.
