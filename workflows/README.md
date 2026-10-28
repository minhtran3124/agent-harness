# workflows/

Workflow scripts for the Claude Code `Workflow` tool. `ship.js` is the autonomous second half of
Harness v5 (epic #338, ADR 0001): it ships 1..N already-triaged tickets to one reviewable PR with
no human in the loop. `/autopilot` asks the owner everything first, then launches it by path:
`Workflow({scriptPath: "<repoDir>/workflows/ship.js", args})`. In a consuming repo the file is at
`.claude/workflows/ship.js`.

## args

`{repo, repoDir, remote, base, slug, tickets: [{n, title, depth: S|M|L, group, deps, confirmed}],
testCmd, lintCmd, fullTestCmd, advisorModel, noAsk, local}`. Tickets of one `group` run in parallel;
groups run in ascending order. One ticket: its PR is the final PR. Several: branch `feat/<slug>`,
sibling PRs into it, a merge agent after each group, one final PR into `base`.

## Phases

1. Setup: validate args, create the integration branch (multi only).
2. Tickets: intent, then plan by depth (S in the prompt, M plan, L research + design + plan + advisor),
   implement, finish (push and PR). A blocked ticket is recorded; its dependents are skipped.
3. Merge: after each group (multi only).
4. Review: `code-review` at a level chosen from diff size and risky paths; findings scoring 50 or
   more get one fix agent each; re-review only the fix commits; at most 2 rounds.
5. Intent review: a plan-blind `intent-reviewer` sees only the request and the diff range.
6. Verify: the full suite once, at the end.
7. Decisions: one artifact, the ADR files (`scripts/write_adrs.py`), and the PR body.

Stage agents run the skill by path with `Mode: auto`, never ask, and return `decisions[]`. Workflow
agents cannot start agents, so the script calls the advisor when a stage sets `needs_advisor`.
Models and effort are constants at the top of the file.

## Local mode

`local: true` pushes nothing and opens no PR: branches stay local and the PR body is written to
`PR-BODY.md` in the final worktree. Use it for dry runs on a scratch repo.

## Tests

`bash tests/scripts/ship-workflow.test.sh` runs `tests/workflows/harness.js`: a Node harness that
loads the script with stubbed `agent()` and records every call. No real agent runs.
