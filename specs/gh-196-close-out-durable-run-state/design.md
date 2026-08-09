# gh-196-close-out-durable-run-state — Design

Most of this issue is prescribed by #196 itself (Part 1 is a rebase of existing work; Part 3 is a
doc refresh + close). The one genuine design fork is **Part 2: how to make terminalization robust
against the integration branch changing.**

## Part 2 — trigger policy fork

The bug: `post-merge-maintenance.yml` fires only on base branches in a static allowlist
(`[main, loop]`). When integration moved to `simplify`, every `simplify`-targeted merge fired
nothing — the `shipped` transition silently vanished. Constraint: `pull_request_target` reads its
definition **and** its branch filter from the repo default branch (`main`), so any fix only takes
effect once merged to `main`.

### Option A — add `simplify` to the static list
`branches: [main, loop, simplify]`, synced to `main`.
- ➕ Smallest possible diff.
- ➖ Rots again the next time the integration branch is renamed — exactly the failure the issue
  says must not recur ("cannot silently disappear merely because the integration branch changes").
  A text-list regression test would only pin today's list, which the issue calls insufficient.

### Option B — base-branch-agnostic trigger (**chosen**)
Drop the base-branch restriction from the trigger; let the job's **existing** guards decide:
`pull_request.merged == true`, head ref not `chore/bookkeeping-*`, and the tracked-run detection
(`specs/<slug>/SUMMARY.md` + `RUN.json` present). A merged PR terminalizes iff it carries a tracked
run — **independent of which branch it merged into.**
- ➕ Directly satisfies "cannot silently disappear merely because the integration branch changes":
  there is no branch list to rot. The policy becomes "any merged PR carrying a tracked run
  terminalizes" — the **one authoritative place** is the job's guard/detection logic, documented in
  a header comment and the canonical docs.
- ➕ The regression test asserts a *policy* (the trigger imposes no base-branch allowlist that could
  exclude the active integration branch), not a text list — the stronger assertion the issue wants.
- ➖ Fires on more PRs (every closed PR, all bases). Mitigated: the `merged==true` +
  `bookkeeping-*` + no-tracked-run guards make non-run PRs no-op in the first seconds; the
  bookkeeping step already exits `changed=false` when there is nothing to record.
- ➖ Still must be merged to `main` to take effect (inherent to `pull_request_target`). The header
  comment and regression test state this explicitly so it cannot be forgotten.

**Decision: Option B.** It is still a small change to the existing flow (no new service/scheduler —
respects the non-goals) and is the only option that removes the rot the issue targets. The
`branches:` narrowing is replaced by a documented, tested, base-agnostic contract.

> Notify-and-proceed: this changes trigger semantics on a high-blast workflow. High confidence,
> reversible (`git revert`). Flagged here for the human to veto; not blocking.

## Reconciliation policy (Part 2, second half)
For each stale `ready_to_merge` run, append exactly **one** `shipped` event via the real CLI
(`run_state.py transition --to shipped --sha <confirmed merge SHA> --event manual.reconcile-gh196`)
so the event chain stays valid under the new validator. Use the confirmed **merge SHA** from
`gh pr view`, never the run head commit, never a hand-written event. Record the one-time repair in
SUMMARY. If a SHA cannot be confirmed, document the run as intentionally unresolved instead.

## Part 1 & Part 3 — no fork
- Part 1: rebase the feat/gh-174 runtime engine + tests onto the worktree; hand-reapply the three
  known conflicts (`subagent-driven-development/SKILL.md`, `test_run_state.py`, `run-tests.sh`).
  The 8-invariant validator and escape hatches are already reviewed on feat/gh-174; keep them.
- Part 3: mechanical doc refresh of the canonical durable-run-state artifacts + the three review
  oracles + branch finish. No design choices.
