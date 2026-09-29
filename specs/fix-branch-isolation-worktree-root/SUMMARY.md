# fix-branch-isolation-worktree-root — Summary

Lane: high-risk
Confidence: high
Reason: edits `hooks/branch-isolation-guard.sh` — the high-blast hard gate forces high-risk; scope is the single root-resolution bug the user asked to fix.
Flags: high-blast, existing-behavior
Affects: hooks/branch-isolation-guard.sh
Input-type: maintenance

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> fi/exitx the branch-isolation hook worktree bug

(The bug, as reported earlier in the same session: the hook reads the branch from `CLAUDE_PROJECT_DIR`, so every Edit/Write inside a linked worktree is denied as "on shared branch main" when the session launched from the main checkout.)

## What changed

`branch-isolation-guard.sh` now resolves the repository root from the checkout that owns an absolute edit path (`git -C <nearest existing dir> rev-parse --show-toplevel`) instead of from `CLAUDE_PROJECT_DIR`. Edits inside a linked worktree on a task branch are allowed; edits to the main checkout from a session launched in a task worktree are now denied — that reverse direction was silently allowed before (the path normalized as outside-root, and the hook read the worktree's branch).

### Rationale

The branch that matters is the one the edited file will be committed on, which is the owning checkout's HEAD. Resolving it from the file keeps the normalizer, specs-only exemption, and break-glass logic unchanged.

### Alternatives considered

- Teach the normalizer to map worktree paths — rejected: it would still read the branch from the wrong checkout.
- Exempt `.worktrees/` paths by prefix — rejected: a prefix says nothing about the worktree's branch (a worktree can be on `main`), and misses worktrees outside the repo.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| guard contract incl. 10 worktree/bypass regressions | `bash tests/hooks/branch-isolation-guard.test.sh` | 0 | 28 passed; each new case failed before its fix, and removing any one guard arm fails ≥1 case | |
| normalizer contract unchanged | `bash tests/hooks/normalize-tool-input.test.sh` | 0 | 19 passed | |
| prefixed-spec compatibility | `bash tests/hooks/spec-prefix-compat.test.sh` | 0 | 11 passed | |
| hook table matches settings | `bash scripts/lint-doc-truth.sh` | 0 | | |

The full suite (`bash scripts/run-tests.sh`) is cited in prose per the verify-row rule.

Verifies: for an absolute `tool_input.file_path`, the guard judges the owning checkout's branch plus every enclosing checkout of a different repository, and git-dir paths by that git dir's HEAD — independent of the launch directory; the break-glass log stays in the launch repo when it is one.
Does not verify: relative paths (Codex `apply_patch`) — those still resolve against `CLAUDE_PROJECT_DIR`/`$PWD`, unchanged.

### Review Findings

Adversarial review of the first fix commit found 3 Important and 3 Minor; fixed in the follow-up commit:
- Nested/foreign repo could re-home the check (new bypass) — owner accepted only when `git rev-parse --git-common-dir` matches the launch repo's.
- `.git/**` of the main checkout editable from a task-worktree session (pre-existing hole) — git-dir paths now resolve to the main checkout.
- Break-glass log followed the payload-chosen root — pinned to the launch root, owner recorded in the log line.
- `file_path` with an embedded newline — left unresolved.
A second re-review found that the common-dir check skipped judgement whenever the launch directory was not this repository (a regression against the first fix), and that `dirname(common dir)` is not a checkout under separate-git-dir or bare layouts. Fixed in the third commit: the launch directory no longer decides anything for absolute paths; git-dir paths are judged by the HEAD stored in the git dir; the newline arm gained a test.
Recorded, not changed: detached HEAD in the owning checkout allows (pre-existing, now reachable only via this repo's own worktrees); sibling hooks still use `CLAUDE_PROJECT_DIR` (below).

### Not auto-verified

- Codex `apply_patch` sessions editing a different checkout than their cwd — reached traceability only; relative patch paths keep the old root resolution by design.
- `--path-format=absolute` needs git ≥ 2.31; on older git `common_dir` is empty, so git-dir paths fall back to launch-root judgement and every enclosing checkout counts as a different repository (stricter for nested worktrees). Not re-tested on old git.
- `hooks/blast-radius-check.sh` and `hooks/ruff-on-edit.sh` still resolve their root from `CLAUDE_PROJECT_DIR`; worktree edits may show as out-of-plan there (non-blocking). Not changed here.

### Rollback

- `git revert <sha>` (single hook + test + doc change; no state migration). Break-glass meanwhile: `BRANCH_ISOLATION_REASON=<why>`.

### Harness-Delta

- none
