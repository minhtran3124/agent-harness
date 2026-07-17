# Design — Phase 2 Wave 1: zero-coupling deletes

Status: proposed · Companions: `research-brief.md` (fresh re-verification), `PLAN.md`.
Source: `docs/reviews/phase-2-deep-review-2026-07-16.md` Wave 1 (merged PR #77); parent: issue #67 Phase 2.

## Goal

Delete the four verified zero-coupling dead-weight items (~375 lines) with zero enforcement loss and zero CI breakage, as the first of three Phase 2 waves. Wave 2 (coordinated deletes) and Wave 3 (owner decisions) are explicitly out of scope.

## Decisions

1. **`context-monitor.py` — plain delete.** Zero refs re-confirmed; no coordinated edits exist by construction. No tombstone note needed — the two review docs record its story.

2. **`REQ.md` — delete + preserve the questions where they are actually used.** Its only living function is as the subject of `docs/research-harness-req-assessment.md`. Rather than leaving that assessment pointing at a deleted file, prepend a short "Source questions (from REQ.md, deleted 2026-07-17)" block quoting the 6 questions verbatim. Rejected alternative: folding REQ.md into README — nothing in README's audience needs a historical research prompt.

3. **`TEST_MATRIX.template.md` — delete template AND all 3 mandates in the same commit.** The review's key insight is that prose claiming a mechanism nothing runs is the same defect class as C5 (unenforced fiction). Replacement wording keeps the true part of each sentence — SUMMARY's `### Verify` is the behavior-to-proof surface:
   - `rules/orchestration.md:62` → single sentence: behavior-to-proof lives in the SUMMARY `### Verify` table (a row per check actually run).
   - `HARNESS.md:53` + `README.md:64` → drop only the TEST_MATRIX clause, keep the `### Verify` clause.
   Rejected alternative: keeping the template "in case": 0/33 uptake over the repo's whole life and a consciously deferred activation (intent-review-stage) is the strongest possible no-demand signal.

4. **Spinner — remove the animation, keep the `step()` contract.** New TTY branch = run work, print `✓ label` (identical success output, no pre-work sleep loop); non-TTY branch unchanged; `SPIN` array deleted; ERR trap untouched. The visible change is cosmetic-only: ~0.36s faster per step and no braille frames. All installer tests (resync-conflict, install-tty-gate, settings-merge, settings-wiring) must stay byte-green — they never pinned the animation (verified).

5. **Lane: high-risk — mechanically forced, not judgment.** `ci-strict-gate.sh` `HARD_GATE_RE` contains `^templates/`; the TEST_MATRIX deletion puts `templates/` in the PR diff, so CI demands a changed high-risk SUMMARY whose Verify table passes `verify_summary.py --check`. The Verify table therefore contains only pipe-free, re-runnable, repo-root commands (the PR #69 lesson).

6. **One PR, one commit-per-task not required** — tasks are independent (disjoint files) but tiny; a single reviewed PR keeps the audit trail simple. Plan is authored in the **markdown task syntax** (first production plan since PR #69 made it the authoring standard — deliberate dogfood).

## Out of scope (guard rails)

- Wave 2 items (check_plan_format, harness-audit check #4, PR_TEMPLATE) — separate plan.
- Wave 3 owner decisions (stacks profiles, agents/PROJECT.md promote, protected-path-guard, agent-memory).
- The three REVERSED items (branch-guard, category_mode, deploy-harness backup/prompt) — must not appear in this diff at all.
- `.claude/` deployed copies — local-only; sync happens at the next user-authorized `deploy-harness.sh` run.

## Risks

- `deploy-harness.sh` is the installer every consumer runs — the trim is surgical (one function body), pinned by 4 existing test suites run in Task 2.1's full-suite gate.
- Removing prose mandates could orphan a reader's mental model — mitigated by keeping the `### Verify` clause (the mechanism that actually exists) in every edited sentence.
- `rules/orchestration.md` deployed-copy drift until next re-sync — accepted, recorded in research-brief.
