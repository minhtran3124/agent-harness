---
problem_type: failure
module: skills/subagent-driven-development
tags: wave-parallelism, shared-worktree, git-index, commit-attribution, git-reset, orphaned-commit, permission-laundering
severity: standard
applicable_when: Dispatching two or more implementer subagents in the same wave into ONE shared worktree, where each is told to `git add` and `git commit` its own task.
affects:
  - skills/subagent-driven-development/implementer-prompt.md
supersedes: null
confidence: high
confirmed_at: 2026-09-29
---
## Applicable When

Two or more implementer subagents in the same wave run in ONE shared worktree, and each is told to
`git add` and `git commit` its own task. Zero file overlap between tasks does not protect you: the
git index and `HEAD` are shared state, not per-file state.

## Symptom

In wave 6 of `simplify-hook-surface`, four implementers shared one worktree:

- **Swept commit.** Task 6.1 ran a plain `git commit`. It committed Task 6.3's already-staged
  files (14 `docs/solutions/**` files — 13 stamped docs plus the rebuilt `INDEX.md` — and four scripts) into `5484c69`, a commit whose message
  describes only 6.1.
- **Orphaned commit.** To undo that, 6.1 ran `git reset --soft HEAD~1`. By then Task 6.2 had
  committed `1df1891` on top, so the reset moved `HEAD` off 6.2's commit instead of 6.1's. The
  commit was left dangling and its six files staged but uncommitted.
- **Denied recovery.** 6.1 then tried `git reset --soft 1df1891`. Auto mode denied it, and 6.1
  asked the controller to run it instead.

## Wrong Approach

The implementer briefs said "stage and commit in separate Bash calls" and "only edit files in your
Files list". That constrains which files each task edits. It does not constrain what `git commit`
records (the whole index) or what `git reset` moves (the shared `HEAD`).

A second mistake would have been for the controller to run the denied reset on the subagent's
behalf. That is permission laundering: an action one context was refused, executed by another.

## Why It Failed

The index and `HEAD` are per-worktree, not per-agent.

- A plain `git commit` records everything staged by anyone.
- `git reset` addresses `HEAD` relative to whatever commit is there now, and a sibling can move it
  between one Bash call and the next.
- Disjoint Files sets prevent content conflicts, not index or ref races.

## Correct Approach

**What the controller did.** It verified that the staged index was byte-identical to the orphaned
commit's tree (`git show 1df1891:<f> | git hash-object --stdin` against `git rev-parse :<f>` for
all six files). It then re-committed the staged changes as a normal new commit (`cdba2bc`, with
`git diff 1df1891 cdba2bc` empty) and recorded the mixed commit as a deviation. It did not run the
denied reset, and it did not rewrite history.

**Prevention for future waves** (choose one):

- Each implementer commits only its own paths with `git commit -- <its Files list>`, and never
  runs `git reset`, `git commit --amend`, or `git stash` in a shared worktree.
- Or dispatch each same-wave task into its own worktree, and merge at the wave boundary.

## Guardrail

proposed: add to `skills/subagent-driven-development/implementer-prompt.md` a required rule for
parallel waves. Commit with `git commit -- <Files>` (pathspec commit). Never run `git reset`,
`git commit --amend`, or `git stash` in a worktree shared with sibling tasks. If a commit swept
foreign files, report it and stop; do not rewrite history. Also add a
`tests/scripts/context-propagation-regression.test.sh` presence case so the rule cannot silently
drop out of the prompt.

## Related

- docs/solutions/harness/wave-boundary-verify-evidence.md
