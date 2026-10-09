# worktree-enter-by-name — Summary

Lane: normal
Confidence: high
Reason: initially classified high-risk because skills/*/SKILL.md trips the `workflow-engine` hard gate; the user lowered it by narrowing scope to one paragraph ("Create isolation") of one skill file, no other skill, rule, hook, or script.
Flags: existing behavior
Affects: skills/using-git-worktrees/SKILL.md
Input-type: harness improvement

### Intent

Original review request (user, Vietnamese, with a screenshot of the permission prompt "permission-root relocation to .../.worktrees/fix/gh-261-sdd-report-handoff — a model-supplied worktree outside .claude/worktrees/"):

> review why every time it show when work with worktree

Approval of the fix, after the review offered three options:

> ok sua skill di theo huong 1

Option 1, as offered in the review: have the skill call `EnterWorktree` with a `name` so the tool creates the worktree under `.claude/worktrees/` (no prompt), keeping `.worktrees/` only as the fallback when the native tool is unavailable.

Lane decision (user, after intake classified high-risk and offered to narrow scope):

> chon 2, PR vao main

(option 2 = narrow scope to lane `normal`; PR base is `main`.)

## What changed

`skills/using-git-worktrees/SKILL.md` "Create isolation" now tells the agent to call `EnterWorktree` with `name: "<type>/<kebab-slug>"` so the worktree is created under `.claude/worktrees/`, and not to enter a hand-made checkout by `path`. It also documents that the tool names the branch `worktree-<name>` (renamed with `git branch -m`) and to confirm the base commit before committing. The `.worktrees/` / `worktrees/` + `git worktree add` route is kept only as the fallback when no native tool exists.

### Rationale

Claude Code prompts whenever the model passes a worktree `path` outside `.claude/worktrees/`; the old skill preferred a manual `.worktrees/` checkout entered by `path`, so every entry prompted. Creating via `name` keeps the worktree inside the trusted root. The branch-rename and base-check notes come from what was observed when dogfooding the tool in this session (branch came out as `worktree-fix+worktree-enter-by-name`, based on `spec-format` rather than `main`).

Independent review (read-only `reviewer` agent) found the first wording `git reset --hard <base>` unsafe: `Bash(git *)` pre-approves it and the condition protected commits, not uncommitted edits. It is now `git rev-parse` comparison plus `git reset --keep <base>`, done before any edit. Review also noted (accepted, not changed): the "parent is ignored" check now covers only the fallback route, because `.claude/` is gitignored here and in consumers; `EnterWorktree` is not in `allowed-tools`.

### Alternatives considered

- Keep `.worktrees/` and accept the prompt — rejected by the user.
- Allowlist the prompt via `permissions` — not confirmed to be possible; not pursued.
- Add `EnterWorktree` to the skill's `allowed-tools` — not done: unverified that the frontmatter accepts it, and out of the narrowed scope.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Full harness suite (doc-truth, skill lint, manifest, 55 suites, pytest) | `bash scripts/run-tests.sh` | 0 | 802 passed, ALL GREEN | |
| SUMMARY lane evidence | `python3 scripts/verify_summary.py --lane worktree-enter-by-name` | 0 | normal-lane evidence present | |

### Not auto-verified

- That `EnterWorktree` by `name` never prompts — reached observation of one run in this session only (no prompt appeared); not re-runnable by a gate.
- That the instruction text reaches an agent that loads the skill and makes it call `EnterWorktree` — traceability only (the text is in the file); no eval run of the skill.

### Rollback

- `git checkout main -- skills/using-git-worktrees/SKILL.md` restores the previous skill text; or revert the PR's merge commit.

### Harness-Delta

- `backlog` — `EnterWorktree` bases the worktree on the current checkout (`spec-format`) rather than `main`, and names the branch `worktree-<name>`; the skill now works around both, but a `worktree.baseRef` setting may remove the base issue.
