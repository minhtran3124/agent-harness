# design — hook project-root resolution

## The defect

Seven hooks resolve the repository root from the hook's own location:

```bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
[ -z "$REPO_DIR" ] && REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"     # 5 hooks
[ -z "$REPO_DIR" ] && REPO_DIR="${CLAUDE_PROJECT_DIR:-...}"        # 2 hooks
```

This is correct only while `deploy-harness.sh` copies hooks *into* the project. Spike evidence
(2026-09-09, this repo, macOS, Claude Code CLI):

| Hook location | `git -C $SCRIPT_DIR rev-parse --show-toplevel` | Exit | Consequence |
|---|---|---|---|
| Inside the project (today) | project root | 0 | correct |
| Outside any git repo | *(empty)* | 128 | falls through to a wrong-but-loud fallback |
| Inside **another** git repo | **that other repo** | **0** | **gate audits the wrong repository and reports success** |

`claude plugin marketplace add <repo>` clones, so row 3 is the ordinary plugin install path.

The two hooks that already name `CLAUDE_PROJECT_DIR` are **not** protected: they consult it only
*after* the `SCRIPT_DIR` probe has already returned a wrong-but-successful answer. The bug is the
ordering, not the absence of the variable.

Not affected: `check-untracked-py.sh` (uses CWD-relative `git ls-files`, deliberately —
see the note in `tests/lib.sh`), `branch-isolation-guard.sh` and `pre-bash-dispatch.sh`
(already `ROOT="${CLAUDE_PROJECT_DIR:-$PWD}"`).

## Fork 1 — what is the root source, and in what order?

- **A. `CLAUDE_PROJECT_DIR` → git-from-CWD → fail.** Chosen.
- B. `CLAUDE_PROJECT_DIR` → git-from-CWD → `SCRIPT_DIR` probe. Rejected: keeps the silent-wrong-repo
  path reachable, which is the whole defect.
- C. git-from-CWD only. Rejected: `CLAUDE_PROJECT_DIR` is the runtime's own answer and is set even
  when CWD has been changed by a compound command.

Why git-from-CWD must stay as the second step: `tests/lib.sh` runs each hook with
`cd "$repo"` and does **not** set `CLAUDE_PROJECT_DIR`. Dropping the CWD step would make all 200+
hook contract tests resolve nothing. The fallback is ordered, not either/or.

## Fork 2 — what happens when no root can be determined?

Hooks do not share one failure posture, so the guard cannot be uniform. `CLAUDE.md` documents the
per-hook contract; the guard preserves it:

| Hook | Posture today | Guard when root is unknown |
|---|---|---|
| `commit-quality-gate.sh` | blocking gate | **exit 2**, named reason |
| `risk-corroboration.sh` | blocking gate | **exit 2**, named reason |
| `blast-radius-check.sh` | warn; exit 2 under `BLAST_RADIUS_STRICT=1` | warn, exit 0 (exit 2 in strict) |
| `branch-guard.sh` | warn only | note to stderr, exit 0 |
| `render-plan-on-write.sh` | non-blocking | note to stderr, exit 0 |
| `ruff-on-edit.sh` | non-blocking | note to stderr, exit 0 |
| `scope-gate.sh` | non-blocking | `additionalContext` note, exit 0 |

Rejected: fail-closed everywhere. Making a PostToolUse formatter block on an unresolvable root
would break edits for a condition it has no stake in — and `CLAUDE.md` states these hooks stay
"fail-visible but non-blocking".

Rejected: silent `exit 0` on unknown root for the two blocking gates. That is the identical
silent-pass this change exists to close.

## Fork 3 — also detect a SCRIPT_DIR/PROJECT_DIR mismatch and report it?

Deferred, not adopted. In a correct deployment the two roots agree, so a mismatch is genuinely
anomalous and would be useful signal. But it is additive diagnostics on top of a fix whose value
is removing a code path; shipping both at once makes the regression surface larger than it needs
to be. Recorded here so the option is not lost.

## Blast radius

`SCRIPT_DIR` is retained in every hook — it is the correct way to locate a hook's own libraries
(`hooks/lib/git-command.sh`, `hooks/lib/lane.sh`). Only its use as a *repo-root* source is removed.
