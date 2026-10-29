# workflows/

Workflow scripts for the Claude Code `Workflow` tool. `ship.js` is the autonomous second half of
Harness v5 (epic #338, ADR 0001): it ships 1..N already-triaged tickets to one reviewable PR with
no human in the loop. `/autopilot` asks the owner everything first, then launches it by name:
`Workflow({name: "harness:ship", args})`. The plugin registers `./workflows/ship.js` in `plugin.json`.

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

No agent uses `isolation: 'worktree'`: it binds to the session's working directory, which is not the
target repo (ADR 0002). Each agent runs `git -C <repoDir> fetch` and `git -C <repoDir> worktree add`
into `<dirname(repoDir)>/.ship-<basename(repoDir)>/<slug>/<name>`, outside the repo, and every prompt
uses absolute paths (skills are read from the agent's own worktree, `skills/` then `.claude/skills/`).
The result's `worktrees` lists the dirs; the script never removes them, so the owner does.

The review stage must invoke the `code-review` skill (`skill_invoked`). If it did not run, the script
retries once; if it still did not run, `review.status` is `not run`, the PR body says
`Review: NOT RUN (<reason>)`, a `needs_review` decision is recorded, and no fix round runs.

`needs_review: true` is only for a decision that affects another ticket, a public contract, stored
data, security or cost, or contradicts the ticket or an owner answer. Reversible in-ticket choices
are recorded with `needs_review: false`. The per-ticket PR line is the stage `summary` (200 characters
at most). `Closes #n` / `Refs #n` are written only when not in local mode.

Scope boundary: the intent stage returns `out_of_scope`, the ticket's own Out of scope lines copied
verbatim, next to `files`. The boundary is those lines plus the files the ticket names (the intent
`files` and the paths in the plan steps); the file set limits production, test and doc files alike
(a test or doc file is in bounds only when the ticket lists it). The implement, review-fix and intent-fix prompts carry it. A change outside it is not made: the
agent returns a decision titled `Boundary: ...` with `needs_review: true`, and a fix returns
`fix_status: skipped`. Such a fix is listed in the PR body `## Review` section as
`needs your decision`. The PR body also gets a `## Needs your decision` section above `## Summary`,
listing behaviour-changing `excess` gaps from the intent review and the boundary decisions that need
review; it is left out when both are empty. `{{DECISIONS}}` stays after Final verification.

Stage agents run the skill by path with `Mode: auto`, never ask, and return `decisions[]`. Workflow
agents cannot start agents, so the script calls the advisor when a stage sets `needs_advisor`.
Models and effort are constants at the top of the file.

## Local mode

`local: true` pushes nothing and opens no PR: branches stay local and the PR body is written to
`PR-BODY.md` in the ADR worktree. Use it for dry runs on a scratch repo.

## Tests

`bash tests/scripts/ship-workflow.test.sh` runs `tests/workflows/harness.js`: a Node harness that
loads the script with stubbed `agent()` and records every call. No real agent runs.
