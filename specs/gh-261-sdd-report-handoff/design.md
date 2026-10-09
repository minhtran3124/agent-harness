# SDD report handoff — design

Written 2026-10-09. Pins: agent-harness `b0d2a92`, issue #261.

**Status:** approved by the user on 2026-10-09 (approach A; the user asked for and received a
comparison of A and B, and an account of how A improves the workflow).

## 1. Goal

The SDD implementer handoff works under the runtime's actual rules. The implementer returns its
full structured report inline. The controller persists that report to
`.harness-state/sdd/report-<task>.md` before building the review package. The task reviewer keeps
reading the report from that path.

## 2. Current state

- `skills/subagent-driven-development/implementer-prompt.md:107` tells the implementer: "Write the
  detailed structured contract below to `[IMPLEMENTER_REPORT_PATH]`, then return only `status`,
  commit SHAs, Verify result, a `Harness-Delta` line, and that report path."
- `skills/subagent-driven-development/SKILL.md:54`: "The implementer reports under
  `.harness-state/sdd/`, returning status, commits, Verify, a `Harness-Delta:` line, and the path."
- `rules/orchestration.md:40-41` (always-on): "Under a file handoff (`subagent-driven-development`),
  the full contract goes in the report file and the inline return carries status, commits, Verify
  status, `Harness-Delta`, and the report path."
- `skills/subagent-driven-development/task-reviewer-prompt.md:21` takes `IMPLEMENTER_REPORT_PATH`.
  `scripts/check_task_review_contract.py` pins that token.
- The Claude runtime refuses a subagent `Write` of a report file ("Subagents should return findings
  as text"). Observed on `opus-5-5-review-bindings` (2/2 implementers, 2026-10-02) and on gh-258
  (4/4, 2026-10-08). On gh-258 the Bash heredoc fallback was also refused by the worktree-isolation
  check.
- Prior art: `docs/solutions/harness/sdd-report-file-handoff-refused-for-subagents.md`, a failure
  track whose Guardrail is `proposed:` and matches approach A.
  `docs/harness-experimental/improvement-backlog.md:23` holds the row, status `open`.

## 3. Approaches considered

| Approach | Verdict |
|---|---|
| **A. Controller owns the file** | **Chosen by the user.** Smallest contract change. The reviewer contract is unchanged, the report file survives re-review rounds and `resume`, and it matches the documented guardrail. |
| B. No report file; the controller pastes the report into the reviewer prompt | Rejected. It changes the reviewer contract (`IMPLEMENTER_REPORT_PATH`, `check_task_review_contract.py` and its test), breaks SKILL.md's "never paste report contents", loses the artifact for re-review and resume, and diverges from the guardrail. |
| Let subagents write the file | Not viable. The refusal is a runtime policy outside the harness. |

## 4. Change

1. **`implementer-prompt.md` Report Format.** Replace the "Write … to `[IMPLEMENTER_REPORT_PATH]`,
   then return only …" sentence with: return the full structured report below in the final
   message; do not write a report file, the controller persists it. The report fields are
   unchanged. `[IMPLEMENTER_REPORT_PATH]` no longer appears in the implementer prompt.
2. **`SKILL.md` Execute waves, first bullet.** The implementer returns the full structured report
   inline. On a `DONE` or `DONE_WITH_CONCERNS` return, before building the review package, the
   controller writes it verbatim to `.harness-state/sdd/report-<task>.md` under a one-line
   "transcribed by controller" header, and passes that path to the task reviewer. After a fix
   dispatch, the controller overwrites the file with the latest report, so the re-review reads the
   current state. A `BLOCKED` or `NEEDS_CONTEXT` return writes no file, because no review follows
   it. Keep "record non-`none` deltas in SUMMARY" and "Never paste history or report contents"
   (into another prompt). Exact phrase for the test: `the controller writes it verbatim to`.
3. **`rules/orchestration.md` Subagent contract.** Reword the file-handoff sentence: under
   `subagent-driven-development` the implementer returns the full contract inline, because the
   runtime refuses subagent report-file writes, and the controller persists it to
   `.harness-state/sdd/` for the task reviewer. Say that this full structured report is what the
   main thread needs, so it does not contradict the next line's "no raw file dumps".
4. **Test.** Extend `tests/scripts/sdd-artifact-handoffs.test.sh` with fixed-string checks:
   - `implementer-prompt.md` contains no `[IMPLEMENTER_REPORT_PATH]` and contains
     `do not write a report file`;
   - `SKILL.md` contains `the controller writes it verbatim to` and `report-<task>.md`;
   - `rules/orchestration.md` does not contain `the full contract goes in the report file`.

   The guardrail text suggested the context-propagation regression test. This test is the
   handoff's own suite, so it is the better home; the intent (a presence case that fails if the
   file-write instruction returns) is the same.
5. **Knowledge loop.** Set the backlog row to `done (2026-10-09, gh-261)`. In the solution entry,
   change the Guardrail to `existing:` naming the changed files and the test, add
   `rules/orchestration.md` to `affects:`, and update `confirmed_at`. Then run
   `python3 scripts/rebuild_solution_index.py`, because INDEX order depends on `confirmed_at` and
   no CI step checks INDEX staleness.

Not changed: `task-reviewer-prompt.md`, `check_task_review_contract.py`, `.harness-state/sdd/` as
the report location.

## 5. Error behavior

- An implementer that writes a file anyway is harmless; the controller's transcription is
  authoritative and overwrites it.
- An implementer that returns a partial report: the controller still writes what was returned, and
  the task reviewer sees the gap. Its spec verdict covers missing Deviations/Blockers. This matches
  the no-report rule in `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md`.

## 6. Tests

- `bash tests/scripts/sdd-artifact-handoffs.test.sh` exits 0 with the new checks.
- `python3 scripts/check_task_review_contract.py` still exits 0 (reviewer contract unchanged).
- `python3 scripts/render_skill_prompt.py --check-all` still exits 0 (implementer and reviewer
  deliveries unchanged).
- `bash scripts/run-tests.sh` exits 0 (cited in prose at finishing).
- Context-propagation audit: the new instruction reaches its consumers. The implementer gets it
  pasted in its prompt; the SDD controller gets SKILL.md; every session gets
  `rules/orchestration.md`.

## 7. Success criteria

1. `implementer-prompt.md` contains `do not write a report file` and no `[IMPLEMENTER_REPORT_PATH]`.
2. `SKILL.md` contains `report-<task>.md` and states that the controller writes it.
3. `rules/orchestration.md` no longer contains "the full contract goes in the report file".
4. The handoff test, the task-review contract check and the prompt matrix check each exit 0.
5. The backlog row reads `done`, and the solution entry's Guardrail starts with `existing:`.

## 8. Non-goals

- Changing the task-reviewer contract or `IMPLEMENTER_REPORT_PATH`.
- Reducing the controller's context. In practice the inline report already reaches it, since the
  file write is refused; the written contract said otherwise.
- Verifying that the controller's transcription is verbatim (judgment-tier; header only marks it).
- #262 (scratchpad writes) and the other open issues.
