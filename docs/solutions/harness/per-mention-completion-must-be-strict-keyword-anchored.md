---
problem_type: knowledge
module: harness
tags: status-log, completion-parsing, resume-cursor, per-mention, keyword-anchored, denylist-antipattern, under-claim-safe, fsm-consumers
severity: standard
applicable_when: Reconstructing which plan tasks are "done" from free-text Status-Log prose (resume cursor, progress rollups) — before you write a permissive "claim by default, suppress on a keyword" parser.
affects:
  - runtime/resume_decision.py
supersedes: null
confidence: high
confirmed_at: 2026-08-10
---
## Applicable When

You must decide, from human-written `## Status Log` bullets, which task IDs are completed — to
build a resume cursor, a progress strip, or any consumer that will SKIP a task it believes is done.
The safety asymmetry is the whole problem: **over-claiming skips real work** (dangerous);
**under-claiming re-dispatches a finished task** whose `Verify` re-runs cheaply (safe).

## Pattern

Detect completion **strict and keyword-anchored**, never "permissive-default + denylist":

- Claim a task ID complete ONLY when it is governed by a `task(s)` keyword — directly, or as a
  member of that keyword's comma/`and`/slash list or hyphen/en-dash range — AND a completion
  marker governs that group.
- A **bare** ID (not under a `task(s)` keyword) is NEVER claimed. This is what safely rejects
  reference decimals (`design 5.4`, `§2.1`, `v1.2`, `Python 3.1`, `coverage 2.1%`) and loose
  mentions (`shipped 1.2 support`, `1.2 not started`) with no denylist at all.
- Suppression of an anchored ID is **positional / completion-governed**: an explicit
  non-completion marker (`pending`/`blocked`/`in progress`) always suppresses; a future marker
  (`will follow`, `next`, `starting`) suppresses only when no completion marker sits *after* it in
  the mention's own cell — so `Tasks 1.1, 1.2 complete, next wave 2` claims both, while
  `Task 1.1 done and Task 1.2 will follow` claims only 1.1.
- Keep commit-SHA attribution **decoupled from clause splitting** — scope each SHA to its own
  mention's neighbourhood in the raw entry, or an em-dash split (`Task 1.1 — \`sha\``) shifts the
  SHA onto the next task.

## How to Use

When the corpus of real Status-Log phrasings is wider than your fixtures (it always is), prefer the
strict model and accept that some entries under-claim — that is the safe direction and it converges.
The opposite ("claim everything in a completing entry, then suppress the bad ones") is a denylist
that can never be made complete: on gh-175 it cycled through three regressions (reopened over-claim
landmine, then over-suppression, then wrong-task SHAs) before the strict rewrite converged. Pin the
semantics with a corpus test (`resume complete ⊆ a completing-entry upper bound`, i.e. no
over-claim) plus a landmine test **swept across separators** `{". ", "; ", ", ", " — ", "\n  - "}` —
the round that regressed did so only for `,` and newline sub-bullets, which `.`/`;`-only fixtures
missed.

## Gotchas

- The visual renderer's done-set (`render_plan.py::_done_task_ids`) is deliberately permissive —
  it marks EVERY ID in a completing entry, so `Task 1.1 complete; Task 1.2 pending` yields both.
  Do NOT reuse it or require parity with it for a resume/skip decision; bound renderer parity to
  ordered task-ID extraction only.
- Two residual over-claims remain accepted in the strict parser and are bounded by the downstream
  fail-closed `checks_to_rerun`/`missing-verify` net: a range member with its own `blocked` marker,
  and the progressive `executing` read as completion. Recorded in the gh-175 SUMMARY
  `### Not auto-verified`.

## Related

- docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md
- docs/solutions/harness/prose-encoded-state-logic-accrues-contradiction-chains.md
