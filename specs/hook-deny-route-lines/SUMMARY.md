# hook-deny-route-lines — Summary

Lane: high-risk
Confidence: high
Reason: high-blast hard gate — edits hooks/commit-gate.sh, hooks/branch-isolation-guard.sh and hooks/lib/
Flags: existing behavior, cross-platform
Affects: hooks/commit-gate.sh, hooks/branch-isolation-guard.sh, hooks/lib/ (deny message text)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/hook-deny-route-lines/intent.md @ 94682f9de82e942dfde2beec11a843238880c245

"trong luc tôi review thì start cho next item theo research doc đi" — after E6, the next item in
the suggested order of `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §6 is E2:

| **E2** | **Audit every deny message for "reason + route to approval"** and add the missing route lines (e.g. "set `BRANCH_ISOLATION_REASON=…`", "record decision in ESCALATIONS.md") | Play 10 | `hooks/commit-gate.sh`, `hooks/branch-isolation-guard.sh`, `hooks/lib/` | high-risk (hooks) |

Scope decision after xia2 (2026-10-14). Question asked: "Should its route gain 'in a separate Bash call, then commit'? That edits a message the design (D2) and intent say stay as they are, so a yes is a design change (DC1) and widens the intent's 'messages that already have both stay' by one message." (about the untracked-`.py` deny whose route `Run: git add <files>` is denied again when combined with `git commit` in one Bash call). User reply:

"yes"

### Intake notes

<!-- Agent-written intake notes (confidence reasoning, assumed defaults, re-pin lines).
     Not part of the intent oracle. `- none` when empty. -->

- Confidence high: one reading (add a route line to each blocking path, no gate behaviour
  change); every `(assumed)` constraint in intent.md is a conservative default the user approved.
- The research note lists E2 as high-risk; the manifest's block-mode `high-blast` gate (`hooks/*`)
  confirms it. Message-text-only scope does not lower the lane.
- Cross-platform flag: Claude and Codex both consume the deny text (stderr / JSON reason).
- Intent committed on `sdlc` first, then moved to branch `feat/hook-deny-route-lines` (local
  `sdlc` reset to `github/sdlc`, unpushed) to match the review-policy precedent that keeps
  `sdlc` as the shared integration branch.

## What changed

Every blocking path in `hooks/commit-gate.sh` and `hooks/branch-isolation-guard.sh` now states a
reason and a route to clearing it. Eleven paths that lacked a route gained a `Route:` line
(redeploy, project root, secrets, `.env`, breakpoint/pdb, failing tests, strict blast radius, and
the unclassifiable-payload deny on both hooks); the one silent block (`cd "$REPO_DIR" || exit 2`)
now prints a reason and route; and the untracked-`.py` deny says to stage and commit in separate
Bash calls (DC1). No condition, exit code, deny decision, profile or mode changed. All 21
blocking paths now have a test asserting their route text (the four hook suites pass: 96, 47, 32
and 53 cases).

### Rationale

<!-- Why this approach — the decision + the key constraint/signal that drove it.
     This is the audit record for autonomous (no-human) work: write it so the
     decision can be reconstructed later WITHOUT re-reading the diff. -->

Inline route lines (approach A) keep each deny self-contained — the lib-missing paths cannot depend
on a shared helper because they fire when a lib is missing — and leave the ten complete messages
byte-identical apart from the DC1 sentence, so the diff is text-only and every existing assertion
still holds.

### Alternatives considered

<!-- Other options weighed + why not. `- none` if it was the single obvious
     approach (typical for tiny lane). -->

- Shared `hook_deny <reason> <route>` helper in `hooks/lib/` — rejected: G2/G3 fire because a lib
  is missing, and it would rewrite the ten complete messages.
- Inline lines plus a lint that every `exit 2` has a nearby `Route:` — rejected: it checks spelling,
  not that the route is real (`ratchet-matches-spelling-not-property`), and is unrequested scope.

### Deviations

<!-- Every Rule 1–3 auto-fix per rules/auto-correct-scope.md, labeled by rule.
     Leave a single `- none` line if there were none. -->

- Decision change DC1 (design.md): D2 superseded by D5 — the untracked-`.py` deny route gains "in a separate Bash call, then commit"; user-approved 2026-10-14.
- Rule 3 — Task 1.1: the plan's `--source <harness>` assertion substring cannot be passed to `assert_rc_contains` (`tests/lib.sh` runs `grep -qF "$2"` with no `--`, so grep parses it as an option); asserted `' --source <harness>'` (leading space) instead. `tests/hooks/commit-gate.test.sh`. Commit `bd09585`.
- Rule 1 — Task 1.2: same cause; asserted `'source <harness>'` instead (still unique to the G11 route). `tests/hooks/branch-isolation-guard.test.sh`. Commit `ba38ba1`.
- Recurring deviation (same cause in two tasks) = a PLAN.md gap in the pinned substrings, not a design problem: both tasks are done and no later task depends on it, so it is recorded here and in Harness-Delta rather than escalated. The two workarounds differ in spelling; both assert text unique to their route.

### Verify

<!-- Evidence over assertion: one row per check that was actually RUN.
     A claim of "done" is only valid with a re-runnable command + its result.
     Do not list a command that was not run.
     The trailing `Criterion` column is optional: name an `SC-n` from PLAN.md §3
     when the row satisfies one; every SC must be covered by >=1 passing row
     (enforced by .claude/scripts/verify_summary.py). Leave blank for rows that map to no SC. -->

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| commit-gate route lines + G5 + D5 | `bash tests/hooks/commit-gate.test.sh` | 0 | 96 passed, 0 FAIL, 0 skip (G5 ran as non-root) | SC-1 |
| branch-isolation G11 + shared-branch routes | `bash tests/hooks/branch-isolation-guard.test.sh` | 0 | 47 passed | SC-2 |
| escalation / run-state / lane-evidence routes | `bash tests/hooks/commit-gate-evidence.test.sh` | 0 | 32 passed | SC-3 |
| risk-corroboration routes | `bash tests/hooks/commit-gate-risk.test.sh` | 0 | 53 passed | SC-4 |
| commit-gate syntax | `bash -n hooks/commit-gate.sh` | 0 | | |
| branch-isolation syntax | `bash -n hooks/branch-isolation-guard.sh` | 0 | | |

### Not auto-verified

<!-- The other half of the panel. `### Verify` above is the CODE-VERIFIABLE side: every
     row there is a command a machine re-ran. This section is the negative scope — what
     this change CLAIMS that no gate checks. Per CLAUDE.md "Gate verifiability", name the
     tier each such claim actually reached:
       traceability — structure matches (an ID exists, a render agrees with its ledger)
       provenance   — evidence re-derived from the source of truth (receipt pinned at base)
       truth        — behavior re-run (command re-executed, exit codes compared)
     Listing an unverified claim here is not a defect; leaving one UNLISTED is — that is
     how a traceability-tier check gets read as proof of truth.
     Use `- none` only when every claim in this SUMMARY is covered by a Verify row. -->

- Every route names a command, variable or file that exists and clears its block — reached
  provenance (each route was written from a read of the installer, the hooks and `tests/lib.sh`);
  the tests prove only that the text is printed, not that following it unblocks.
- The 21-path inventory is complete — reached provenance (grep of `hooks/*.sh hooks/lib/*`,
  2026-10-14); no gate enumerates blocking paths.
- Codex shows the deny text to the model — not verified; the Codex hooks docs are silent on
  PreToolUse model visibility (research-brief Evidence Boundary).
- G5 coverage on a root runner — the G5 test skips as root; CI runners are non-root.

### Rollback

<!-- Required for any high-risk / Rule-4 action: the exact command(s) to undo it.
     For reversible tiny/normal work, `git revert <sha>` is sufficient. -->

- `git revert bd09585 ba38ba1 698cbdf` — restores both hooks' message text and drops the new
  assertions; there is no state, config or data to undo (text-only change).

### Task review Minors

<!-- Non-blocking task-review findings, forwarded to the final review chain. -->

- Task 1.1 (plan-mandated, SC-1) — `tests/lib.sh:82,86` grep without `--`; worked around with `' --source <harness>'`. Recorded under Deviations and Harness-Delta.
- Task 1.1 (quality) — `tests/hooks/commit-gate.test.sh:372` G5 test leaves its `trap … EXIT` installed for the rest of the file; harmless today (no other EXIT trap in `tests/lib.sh` or the file), would shadow one added later. Optional `trap - EXIT` after the `chmod 755`.
- Task 1.2 (plan-mandated, SC-2) — same `tests/lib.sh` grep cause; worked around with `'source <harness>'`.
- Task 1.3 — none.

### Harness-Delta

<!-- What friction did this task reveal about the workflow itself?
     fix-direct (done in this task) or backlog (-> compound -> docs/solutions/).
     Leave `- none` if the workflow needed no change. -->

- backlog — `tests/lib.sh` `assert_rc_contains` / `assert_rc_not_contains` (lines 82, 86) should use `grep -qF -- "$2"`: any assertion substring starting with `-` is parsed as a grep option today (found by Tasks 1.1 and 1.2).
- backlog — `scripts/install-harness.sh` default `REPO_URL` and its `--help` example name `minhtran3124/harness-skills`, while `README.md:84` uses `minhtran3124/agent-harness` (found by the design review).
