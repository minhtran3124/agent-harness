# QA gaps pilot: what the qa-verifier check found on real tickets

Pilot for #620, after #618 (the `qa-verifier` agent) and #619 (up to 3 fix rounds). Three tickets of kind `docs`
ran through `plugins/harness/workflows/ship.js` at the head of `feat/qa-gaps`, not in local mode. Base of every
ticket PR: `feat/qa-gaps`.

## How the pilot ran

- **Launch.** `/harness:autopilot` is interactive and the session plugin was older than `feat/qa-gaps`. So the
  tickets were triaged by hand and launched with `claude -p --plugin-dir <pilot worktree>/plugins/harness`, which
  calls `Workflow` with `scriptPath` on the pilot worktree's `ship.js`. One single-ticket run per ticket.
- **Agent path.** The run journals show agent type `harness:qa-verifier` for every QA check. The agent type
  resolved, so the frontmatter tool limits were in force. The fallback path (role file, with Edit and Write) did
  not run. The #460 QA agent used only `Bash` and `StructuredOutput`.
- **Depth.** Set by hand to M for every ticket (no `intake` run). Depth S would have skipped the check. #460 is a
  small change that intake might call S; M was forced so that the check runs.
- **Cost figures are estimates.** No run printed a cost. Each figure comes from the token counts in the agent logs
  and typical Sonnet prices that I did not verify. Treat them as rough.
- **Part 2 (tickets with an app) was not run.** No project with an app and a `verify.config.json` was chosen for
  the pilot.
- **Tickets that were dropped.** #311, #314, #265 and #266 name files that no longer exist, so they are stale:
  #311 names `templates/INTENT.template.md` and a sentence that is not in `compound/SKILL.md`; #314 names
  `skills/finishing-a-development-branch/references/pr-body.md`; #265 and #266 name `scripts/check_plan_contract.py`,
  which is gone. #482 documents sandbox scripts that are not in the repo yet. The owner may want to close or
  rewrite them. They were not edited or closed.

### Ticket #460

README "Read by" line (docs). Run `wf_b4a97f59-925`, PR #624, merged into `feat/qa-gaps`.

- **Check result:** `passed`, on commit `c930d1c4`.
- **AC rows:** 5 rows. `PASS` 5 (AC1, AC2 as `ac`; CHG1, EDGE1 as `extra`; NEG1 as `negative`), `FAIL` 0,
  `not-checkable` 0. The check also listed EDGE1 under `non_ac_failures` (see the defects below).
- **Fix rounds used:** 0. The advisor did not fire.
- **Agent calls per stage** (from `run_report.py`): 1 each for `qa`, `implement`, `verify`, `QA check`,
  `security gate`, `finish`, `intent`, `intent review`, `code-review`, the suite run, the ADR stage and the
  artifact stage; 3 for `write specs/ early`. `QA check`: 1 call.
- **Tokens and time:** whole run 21 agents, 34,040 output tokens, 607 agent-seconds. `QA check`: 61.8 s, 1,918
  output tokens (the agent log shows about 26k cache-write and 127k cache-read tokens; about $0.19 by estimate).
  Whole run about $8.6 by estimate.
- **Found by the check and by no other gate:** the two README files were not byte-equal, although the ticket said
  to keep them equal. The differences were older than the change (the "Written by" wording, a Decisions line,
  `applicable_when`, a Checks section). The suite was green and the review had 0 findings. The check recorded it as a
  `needs_review` decision. The owner chose to make the files byte-identical, which was done in commit `12770f22`.
- **Defects found by hand after the run that no gate found:**
  - Making the files equal broke `scripts/lint-doc-truth.sh` (a script path that only exists in the harness repo).
    The lint is a gate; it caught this when the fix ran, not during the pilot run. The fix added the words
    "harness repo" in the Checks section.
  - The blind acceptance test `tests/acceptance/460-readme-read-by.test.sh` (written before the code) had a check that
    no line outside the bullet changes. It failed once the owner chose byte-equal files, and was changed to check
    byte-equality.
  - The headless session ended near the last stage, so the `specs/` flow files for #460 were not written.

### Ticket #591

`write_adrs.py` edge cases (script, kind `docs`). Run `wf_b25e7711-211`, PR #625 (open, CI green on all 3 jobs; it was not merged and stays open, because the real run lacks the suite, ADR and merge-readiness stages).

- **Check result:** `not run` in the real run. The headless session hit its 10-minute ceiling and stopped the
  workflow while the QA check agent was running (4 tool calls, no result). A QA-only follow-up ran afterwards: one
  `harness:qa-verifier` agent, called from a headless session, against a fresh checkout of the PR head. **That follow-up
  is not a ship.js run.** Its result: `passed`, on commit `63439f7f`.
- **AC rows (follow-up):** 6 rows. `PASS` 6 (AC1, AC2a, AC2b, AC2c as `ac`; the branch test file as `extra`; main's
  script as `negative`), `FAIL` 0, `not-checkable` 0. The agent showed that each of the three new tests fails on
  main's script and passes on the branch (exactly 3 failed, 59 passed on main). It said it did not check whether the
  three cases are the right set.
- **Fix rounds used:** 0. The advisor did not fire.
- **Agent calls per stage** (from `run_report.py`, real run, partial): 1 each for `qa`, `implement`, `verify`,
  `verify-retry`, `QA check` (stopped), `finish`, `intent`, `intent review`, `code-review`, `run fix` (1 call for the review
  fix); 3 for `write specs/ early`. No suite, ADR or artifact stage ran.
- **Tokens and time:** real run 17 agents, 36,195 output tokens, 607 agent-seconds (about $7.2 by estimate). QA-only
  follow-up: 1 agent, 4.6k output tokens (about $0.30 by estimate).
- **Found by the check and by no other gate:** nothing. The check confirmed the tests are real repros.
- **Defects found by hand after the run that no gate found:** none found; I did not review the diff by hand. The
  PR body says "Verify result: flaky" (the verify stage needed a retry). Merge-readiness, ADR and suite results are
  missing because the run was cut off.

### Ticket #321

Brainstorming step 2 tier boundary (skill prose, kind `docs`). Run `wf_596bd115-74c`, PR #626 (CI green on all 3
jobs, no open decision; merged into `feat/qa-gaps` as f5bd0ef1). Scope: step 1 of the ticket only (the sentence). Steps 2 and 3 (a blind run) were excluded
by the owner-confirmed text for this run.

- **Check result:** `passed`, on commit `cbef5d25`.
- **AC rows:** 6 rows. `PASS` 4 (S1, S2 as `ac`; N1 `negative`; E1 `extra`), `FAIL` 0, `not-checkable` 2 (S3: the
  new text stays in STE, a judgment; S4: the blind-run criteria, which no command can show). Reported separately as
  asked.
- **Fix rounds used:** 0. The advisor did not fire.
- **Agent calls per stage:** 1 each for `qa`, `implement`, `verify`, `QA check`, `finish`, `intent`, `intent review`,
  `code-review`, the suite run, the ADR stage and the artifact stage; 3 for `write specs/ early`. Every stage ran.
- **Tokens and time:** whole run 20 agents, 41,491 output tokens, 549 agent-seconds (about $8.6 by estimate). `QA check`:
  60.6 s, 1,639 output tokens (about $0.15 by estimate).
- **Found by the check and by no other gate:** nothing. Suite: 911 passed, 0 failed, 4 skipped.
- **Defects found by hand after the run that no gate found:**
  - `summary.md` written by the run still says `Date: {{DATE}}`.
  - The run stats list no model for the `intent review` stage.
  - The run did not remove its 8 worktrees under `projects/.ship-agent-harness-pilot/321-brainstorm-tier/`.
  - The E1 row says the exit code of the first command was not captured. That is weaker than the agent's own rule
    (command and exit code recorded).

## Summary table

| Ticket | Check result | Commit | Rows (PASS / FAIL / not-checkable) | Fix rounds | Advisor | QA call (time, output tokens) | Run cost (estimate) | Final status |
|---|---|---|---|---|---|---|---|---|
| #460 | passed | `c930d1c4` | 5 / 0 / 0 | 0 | no | 61.8 s, 1,918 | about $8.6 | merged (after an owner-chosen fix) |
| #591 | not run (real run cut off); QA-only follow-up passed | `63439f7f` | 6 / 0 / 0 (follow-up) | 0 | no | 33 s (cut off); follow-up not timed | about $7.2 + $0.3 | PR open, incomplete run |
| #321 | passed | `cbef5d25` | 4 / 0 / 2 | 0 | no | 60.6 s, 1,639 | about $8.6 | merged, run complete |
| Total | | | 15 / 0 / 2 | 0 | 0 | | about $24.7 | |

## Defects found in the QA stage itself

1. **A row can contradict itself.** In #460 the agent gave EDGE1 status `PASS` and also listed it under
   `non_ac_failures`. The `ship.js` code treats only `non_ac_failures` as a problem, so the ticket still got a decision, but
   the row and the list disagree.
2. **Wrong title for a docs ticket.** The decision for a failed negative or extra row is titled `UAT EDGE1 failed for #460`
   (for example). `ship.js` renames the "not run" and "AC failed" titles to `QA check` for a docs ticket, but not this one.
3. **Headless sessions end after 10 minutes.** A `claude -p` session stops a background workflow 10 minutes after its last
   turn. This stopped #591 during its QA check and #460 during its last stage. It was avoided for #321 by a prompt that keeps
   the session taking short turns. The cause is the print-mode setting `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`; the pilot
   could not set it as an env prefix under the owner's permission rule.
4. **Missing `specs/` files.** #460's `specs/` flow files were not written because of item 3.
5. **Weak evidence in one row.** #321's E1 row records no exit code for its first command (see above).
6. **Run-level defects** seen on #321 (not specific to the check): the unfilled `{{DATE}}`, the missing model on the
   `intent review` stage, and the worktrees left behind.

## Answers

1. **How many AC rows were `not-checkable`?** 2 of 17 rows (12%) over the three tickets. Counting only rows of kind `ac`
   (and `not-checkable` rows that stand for an AC): 2 of 10 (20%). Both were on #321, a prompt-and-skill ticket whose pass
   mark is a blind run. On #460 and #591, 0 of 11 rows. Part 2 (tickets with an app) was not run.
2. **How many failures did the check find that the suite and the review did not?** 1, and it was not an AC failure: #460's
   two README files were not byte-equal (found by the check, missed by the green suite and the clean review). AC failures: 0
   of 3 tickets, so the 3-round fix loop (#619) was not exercised at all in this pilot.
3. **What did one check cost?** About 33 to 62 seconds and 0.7k to 1.9k output tokens per call. By my token-based estimate
   (prices not verified): about $0.15 to $0.20 for a check inside a run, about $0.30 for the QA-only follow-up. This is
   about 2% of the estimated cost of a whole run ($7 to $9). No cost was measured; treat the dollar figures as `unknown`
   beyond this order of magnitude.

## Decision rule and result

The rule: if more than half of the AC rows are `not-checkable`, or the check found nothing in every ticket, the owner
decides whether to keep the `qa-verifier` stage.

- More than half `not-checkable`: no (12%, or 20% of AC rows).
- Found nothing in every ticket: no. It found no AC failure, but it did find one non-AC problem (#460), so the second
  condition is not met by a strict reading. The evidence is thin: 3 tickets, 0 AC failures, 1 finding.

The owner still decides. My reading, from this data only:

- **Keep the `qa-verifier` stage.** It is cheap (about 2% of a run), it ran with its tool limits in force, it ran no edit,
  and it caught one real gap that the suite and the review missed.
- **The 3-round loop is unmeasured.** No check failed, so no fix round ran. Keeping it costs nothing when no check fails;
  its value is unknown.
- **Before relying on it,** fix defects 1, 2 and 5 above (row consistency, the title, the missing exit code), and open
  their own tickets. The pilot does not change `ship.js` or any agent file.
