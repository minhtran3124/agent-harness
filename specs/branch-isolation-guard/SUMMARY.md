# branch-isolation-guard — Summary

Lane: high-risk
Confidence: high
Reason: Diff touches hard-gate paths — a new PreToolUse hook (`hooks/branch-isolation-guard.sh`), its registration in `settings.json`, and three core execution skills. High-blast-file gate forces high-risk.
Flags: high-blast-file
Affects: hooks/, settings.json, skills/{writing-plans,subagent-driven-development,executing-plans,using-git-worktrees}
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`.

### Intent

> "tại sao hiện tại khi viết plan xong và bắt đầu implement thì ko có tự tạo branch - git work tree"
>
> Fix directions chosen by the user: (1) wire `using-git-worktrees` into `writing-plans`; (2) sửa logic Step 0 từ `main/master` sang danh sách shared branch cấu hình được; (3) thêm hard-gate hook block Edit/Write trên shared branch khi chưa có worktree.
>
> "review qua thu https://github.com/obra/superpowers, xem họ auto đoạn đó ntn?" → then "ok" to port upstream's native-tool-first + detect-existing-isolation into `using-git-worktrees`.

## What changed

Branch/worktree isolation before implementation went from prompt-only to enforced. Added a PreToolUse `Write|Edit` hook that hard-blocks code edits on a shared branch (`HARNESS_SHARED_BRANCHES`, default `main`/`master`) while a plan is `status: active` (break-glass `BRANCH_ISOLATION_REASON`; `specs/*` exempt); wired `using-git-worktrees` into the `writing-plans` handoff; broadened the execution skills' Step 0 to the configurable shared list; and ported upstream's native-tool-first + detect-existing-isolation patterns into `using-git-worktrees`.

### Rationale

The branch-creation step was structurally orphaned (no skill invoked it, no hook enforced it; `branch-guard.sh` only warns at commit time). A PreToolUse hook makes "isolate before implementing" structural at write time, while staying narrow (only on a shared branch + active plan) so it never fights this meta-repo's own dev on `v2` or the tiny lane. Verified against upstream `obra/superpowers`: the gap was inherited, and upstream is also prompt-soft — this goes further with a real gate.

### Alternatives considered

- Soft warning only (like `branch-guard.sh`) — rejected: a warning after the work is already on the branch is what created the gap.
- Tying the block to branch name alone (no active-plan condition) — rejected: would block tiny-lane edits and harness self-development.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Hook contract suite | `bash tests/hooks/branch-isolation-guard.test.sh` | 0 | 6/6 cases: allow / deny / specs-exempt / feature-branch / break-glass / env-override |
| Doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | hook table in CLAUDE.md matches settings.json registration |

### Rollback

- Revert the change: `git revert <sha>`
- Or manually: remove the `Write|Edit` PreToolUse entry for `hooks/branch-isolation-guard.sh` from `settings.json`, delete `hooks/branch-isolation-guard.sh`, and remove its row from the CLAUDE.md hook table.

### Harness-Delta

- fix-direct — this work itself closed a workflow gap (branch isolation was unenforced). No further backlog item.
