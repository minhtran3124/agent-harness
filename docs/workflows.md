# workflows/

Workflow scripts for the Claude Code `Workflow` tool. `ship.js` is the autonomous second half of
Harness v5 (epic #338, ADR 0001): it ships 1..N already-triaged tickets to one reviewable PR with
no human in the loop. `/autopilot` asks the owner everything first, then launches it by name:
`Workflow({name: "harness:autopilot-run", args})`. The plugin registers `./workflows/ship.js` in `plugin.json`.

## args

`{repo, repoDir, remote, base, slug, tickets: [{n, title, depth: S|M|L, group, deps, confirmed}],
testCmd, lintCmd, fullTestCmd, advisorModel, noAsk, local}`. Tickets of one `group` run in parallel;
groups run in ascending order. One ticket: its PR is the final PR. Several: branch `feat/<slug>`,
sibling PRs into it, a merge agent after each group, one final PR into `base`.

## Merge policy

The workflow merges only ticket PRs into the run's integration branch `feat/<slug>`, and only after a per-ticket gate.
Every PR into `base`, `main` or the default branch is a human merge, and so is the final PR. A single-ticket run never
merges: its PR is the final PR (`Merge: human`). Every PR the workflow opens carries a `Merge: auto|human` line and a
readiness checklist (CI, review, intent, needs_review ADRs, UAT) between `<!-- merge-policy -->` markers.

- **Gate stage** (`stageGate`, multi-ticket remote runs, after finish): a code-review of the ticket PR against `feat/<slug>`
  with fix rounds on the ticket branch, a one-ticket intent review (a code fix it lands is reviewed too), and `gh pr checks`
  on the ticket PR (waits up to 10 minutes). The script judges the results: CI green with at least one passing check
  (no checks = fail closed; pending after the wait = fail), no not-fixed finding and no leftover scoring 50 or more, intent
  verdict `match`, and no `needs_review` decision on the ticket.
- **Merge stage**: merges only tickets that passed, with `gh pr merge <pr> --repo R --merge --match-head-commit <sha>`, the
  head the gate judged. There is no conflict path: a conflict or any failure changes nothing, and the ticket stays open.
- **A ticket that fails a gate** is `blocked` ("human merge: gate <names> failed"), keeps its PR, and gets a `needs_review`
  decision with the exact command `gh pr merge <pr> --repo R --merge`. It is missing from the final PR and its dependents are skipped.
- **Guard**: the `merge-guard.sh` PreToolUse hook blocks any merge whose PR base is not `feat/*`; it fails closed
  (`docs/hooks.md`). Whether plugin PreToolUse hooks fire for Workflow agents is not proven (spike for #516 could not run
  a nested Workflow), so `/harness:setup` offers no `gh pr merge` allow rule and ticket PRs stay human-merged unless the owner allows them.
- **Local mode** has no PRs: there is no guard, no gate and no CI check. The merge stage runs `git merge --no-ff` and
  `git merge --abort` on a conflict. The PR body block still renders in `PR-BODY.md`, with CI as `n/a (local mode)`.

## Phases

1. Setup: validate args, create the integration branch (multi only).
2. Tickets: intent, then plan by depth (S in the prompt, M plan, L research + design + plan + advisor),
   a ground check (below), implement, verify, finish (push and PR). A blocked ticket is recorded; its dependents are skipped.
   Verify runs the `harness:verify` skill in the implement worktree against the issue's `Verify:` row
   (default agent, not read-only). A failure gets one retry: a pass on retry is `flaky`, a second failure
   blocks the ticket and comments on the issue. FE and FE+BE tickets also run the steps on the base commit
   in a separate worktree (base mode); they must fail there, else the ticket is blocked as a weak test.
   BE and docs tickets skip the base check. After the checks, `ship.js` builds one GIF from the stills in
   `.playwright-mcp/<ticket>/` with ffmpeg (palettegen, at most 30 s, 800 px wide, under 10 MB); a missing
   still, a missing ffmpeg or an error gives no GIF and a log line. The result (`pass` or `flaky`, stills,
   GIF path) goes to the finish stage. A separate attach step runs after finish, only when a PR exists
   (not local mode), a GIF exists and the result is `pass` or `flaky`: `gh pr comment --attach` (gh 2.99.0
   or newer), and a `flaky` result also adds a note to the PR body. An attach failure is logged and never
   blocks the ticket. Evidence stays uncommitted (Git ignores `.playwright-mcp/`). Local mode skips verify.
   The manual run on a repo with a real web app is an owner checklist item, not part of the automated
   acceptance: the ticket (#414) stays open until the owner has done and recorded it.
   The final PR body lists each ticket's verify result in a `## Verify` section (after `## Review`,
   before `## Intent review`): kind, result, base check, stills folder and whether the GIF was built
   and attached. Local mode and tickets that never ran the stage add no line.
   Ground check (depth L and M, not S): before implement, `plugins/harness/scripts/ground-check.sh` checks the
   claims of the research brief, design and plan against `integRef` (never the checkout): `path:line` citations
   and their quotes, paths, symbols, `Done-when` command paths and the `Pins` sha. A path or symbol followed by
   `(new)` is exempt. Depth L checks the brief and the design in full mode, then the plan in paths-only mode;
   depth M checks the plan in paths-only mode. A failed check re-runs the design or plan once with the failed
   claims; a second failure asks the advisor, records a `needs_review` decision and blocks the ticket before
   implement. The gate fails open: when the cheap ground agent gives no answer, exits 2 or copies a text
   wrongly, the log says ground did not run and the ticket continues.
3. Merge: after each group (multi only).
4. Review: `code-review` at a level chosen from diff size and risky paths; findings scoring 50 or
   more get one fix agent each; re-review only the fix commits; at most 2 rounds.
5. Intent review: a plan-blind `intent-reviewer` sees the request, the diff range and the owner-confirmed block, never the plan.
6. UAT: a plan-blind acceptance test of the running app (`skills/uat`), serial over the tickets, for FE, BE and
   FE+BE tickets (docs tickets and local mode skip it with a log line). The agent gets the issue body and the
   owner-confirmed block with every `Verify:` row stripped in code, and the config path verify used; it never
   sees the plan or the diff. 3 to 8 scenarios, each naming an AC id, `negative`, `extra` or
   `not-browser-checkable`. An AC failure gets one fix round and one rerun in a fresh worktree; a second
   failure marks the ticket blocked with reason `UAT AC failed` (code stays, the PR still opens, `Refs`
   instead of `Closes`). A negative or extra failure, or a run that could not happen (no config, app will
   not start), becomes a `needs_review` decision and the ticket stays done. The PR body gets a
   `## UAT sign-off` checklist that nothing enforces.
7. Testing: the full suite once, at the end.
8. Decisions: one artifact, the ADR files (`scripts/write_adrs.py`), and the PR body.

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
Models and effort are constants at the top of the file. `stageModel(stage, depth)` picks Opus for the design and plan stages at depth L and keeps Sonnet for the plan stage at depth M. Depth L is the difficulty signal, so this fixed rule fits "the orchestrator chooses the model per task difficulty"; there is no args override.

## Local mode

`local: true` pushes nothing and opens no PR: branches stay local and the PR body is written to
`PR-BODY.md` in the ADR worktree. Use it for dry runs on a scratch repo.

## Tests

`bash tests/scripts/ship-workflow.test.sh` runs `tests/workflows/harness.js`: a Node harness that
loads the script with stubbed `agent()` and records every call. No real agent runs.
