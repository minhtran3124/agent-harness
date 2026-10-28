---
ticket: 347
stage: implement
status: accepted
needs_review: false
confidence: high
decided_by: claude (main session)
date: 2026-10-28
---

# 0002. What the first real run of ship.js showed

## Context

`workflows/ship.js` ran for real once: one ticket (a `median()` function), `local: true`, on a throwaway repo. The session working directory was a different repo (the harness checkout). The ADR format follows 0001.

## Results

What worked: every stage ran; the intent review stayed plan-blind; local mode pushed nothing and opened no PR or artifact; the code was correct; 8 ADRs were written.

What did not work:

- **D1.** The review agent did not run `code-review`. It judged the diff small, read it itself, and returned 0 findings. The script took that as a pass.
- **D2.** Agents with `isolation: 'worktree'` got a worktree of the session repo, not of `args.repoDir`. The review, intent, suite and ADR agents ran there, the ADR commit landed in the wrong repo, and agents read old skill files from the wrong checkout.
- **D3.** 5 of 8 ADRs had `needs_review: true` for trivial in-ticket choices (even-length median, `ValueError` on empty input).
- **D4.** The intent reviewer looked for its role file under the wrong root, emitted `unknown` findings about its role file and "tests pass", and read the diff in another repo.
- **D5.** The per-ticket PR line was raw agent narration ("Nothing was pushed... The full suite was not run.") that contradicted the Final verification section. `Closes #1` was written for a ticket that is not a real issue.
- Cost: about 500k subagent tokens and 3.5 minutes for a 12-line change with 8 agents.

## Options

1. Keep `isolation: 'worktree'` and pass the repo some other way. Rejected: isolation is tied to the session cwd.
2. Every agent creates its own worktree of `repoDir` with `git -C`. Chosen.
3. Trust the review agent's word. Rejected: this is D1.

## Decision

1. No agent uses `isolation`. Each agent runs `git -C <repoDir> fetch <remote>` and `git -C <repoDir> worktree add` into `<dirname(repoDir)>/.ship-<basename(repoDir)>/<slug>/<name>` (outside the repo). Branch-creating stages use `-b`; read-only and final-branch stages use `--detach` at the ref. Every prompt says the session cwd is not the target repo and uses absolute paths, including for skill and role files. The result lists the worktree dirs; the script never deletes them.
2. The review result carries `skill_invoked` and `skill_error`. One retry with the error; then `review.status = 'not run'`, a `needs_review` decision, and `Review: NOT RUN (<reason>)` in the PR body. No fix rounds run for a review that did not run.
3. `needs_review: true` only for effects on another ticket, a public contract, stored data, security, cost, or a contradiction of the ticket or an owner answer.
4. The intent reviewer gets an explicit role-file path (worktree, then `.claude/`, then inline text), reads the diff in its own worktree, and the `unknown` kind is gone.
5. The PR body line per ticket is the stage `summary`, capped at 200 characters. `Closes`/`Refs` only when not local; local mode writes `Ticket n`.
6. This ADR and the README update.

## Why

Each fix removes a way for the script to report success it did not observe, or to act on the wrong repo.

## Consequences

- Leftover worktrees under `.ship-<repo>/<slug>/` need removal by the owner (`git -C <repoDir> worktree remove <dir>`).
- A retry of a stage reuses its worktree dir when it exists.
- A skipped review is visible in the PR body and the decision list, and the pipeline still ends.
- Cost per run is unchanged; this run's cost is a separate concern.

## How to reverse

Revert the commits `fix(workflows): own worktrees ... (#347)` and `test(workflows): pin the real-run fixes ... (#347)`. Supersede this ADR with a new one.
