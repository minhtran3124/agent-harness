# gh-318-diagnosing-bugs — Review ledger

Controller ledger for per-task review results. It holds what goes into `SUMMARY.md` at finish.
SUMMARY stays uncommitted until every Success Criterion has a Verify row, because the commit gate
runs `verify_summary.py --lane` on a staged SUMMARY.

## Minor findings (task review, for the final review chain)

- Task 1.1 — `skills/diagnosing-bugs/SKILL.md` Phase 3, 4 and 6 `Done when:` lines leave out a criterion that the phase body states (posted to the user; diagnosis.md committed; leftover harness deleted). No behavior is lost. The file has 6 words of headroom.
- Task 1.1 — `references/diagnosis-review-prompt.md` return YAML has no `meaning:` and no `checked_against:` keys, which `rules/review-policy.md` names for the task reviewer.
- Task 1.1 — Only a template comment keeps the probe tag unbracketed in `diagnosis.md` `Probes:`. A bracketed tag there would match the Phase 6 `[DEBUG-` search.
- Task 1.2 — `task-reviewer-prompt.md` step 4 skip depends on `diagnosis.md` `Seam:`, but the reviewer's inputs do not say where it reads that line.
- Task 1.2 round 1 Minors 1–3 (exemption trigger, plan-format "Otherwise", named `NEEDS_CONTEXT` rule) were fixed in `28b9aa2` and re-reviewed clean.

- Task 2.1 — `skills/writing-plans/SKILL.md:32`: after the split, "Keep the `- Plan-contract: 2` marker." no longer carries the "When `diagnosis.md` exists" condition. No behavior change, because step 3 already requires the marker on every new plan. Accepted.
- Task 2.2 — the `Input-type: bug fix → diagnosing-bugs` handoff text sits on a third continuation line of the `feature-intake` entry, not the first line. Same meaning. Accepted.

- Task 3.1 — SC-28 (DC2) is traceability tier: it shows a tool call named the skill path, not that the read succeeded. The extractor prints no tool results. The implementer checked `is_error=False` by hand for each read.
- Task 3.2 — the loop-command input `loop.sh` was chosen after the run (labelled Rule 1; it is a judgment call). The outcome was the same either way. Task 5.1 now pins the input rule before its run.
- Task 3.2 — the PROBE-before-HYPOTHESIS precedence can hide an `H1` line in a `diagnosis.md` Write that also holds `[DEBUG-` records. D16 moves the list into reply text, which avoids this.
- Task 3.2 — the "can pass" path of `check_replay.py` rests on hand-made fixtures that were not committed. Task 5.1's real result is the evidence.
- Task 3.2 — the run's `Loop:` field (`$SCRATCH`) differs from the command it ran (`$S`). This is a skill-side finding, recorded only.

- Task 3.1 round 1 — the `(sub) ` prefix keeps subagent calls out of SC-26/SC-28, and also out of the negative SC-27/SC-29. Those two cover main-thread calls only. In the recorded logs the only subagent lines are two Reads of the run's own `diagnosis.md` and `SUMMARY.md`.
- Task 3.1 round 1 — the ` … [paths: ...]` note marks a path named past the cut, read or not. SC-28 still matches on its own line 10 (a direct `sed` read).

- Task 6.1 — "Continue on your own ranking" was dropped; nothing tells the agent to probe in rank order. D17 does not require it.
- Task 6.1 — the template comment "One probe for each prediction." states coverage; the one-probe-to-one-hypothesis rule now lives in the `tests: H<n>` field shape.
- Task 6.2 — the HYPOTHESIS rule cannot tell which file a heredoc writes, so an unrelated early `H1` line could make the SC-30 order pass falsely (never fail falsely). Task 7.1's first HYPOTHESIS line is checked by hand.

- Task 9.1 — the dispatch sentence "Dispatch the `task-reviewer` to Read <path> first and follow it." holds two actions. Not fenced, ste-lint 0. The file has 1 word of headroom.
- Task 8.1 — four Minors folded into SUMMARY `### Not auto-verified` (DC6 post-run rule, `"$PWD"` input, PROBE false positive, implementer-reported green and clean-clone state). The strict conversion was confirmed byte-identical by the controller.

## Fix rounds

- Task 1.2 — round 1 (`28b9aa2`): three Minors applied; re-review pass/approved, no findings.
- Task 1.3 — round 1 (`52b3416`): Important spec finding fixed (seam point compared with the whole `diagnosis.md` `Seam:` value); re-review pass/approved, no findings.
- Task 2.1 — round 1 (`725fd33`): two Minors applied (route keyed on `Input-type: bug fix`; writing-plans sentence split); re-review pass/approved, one new Minor (above).
- Task 2.2 — round 1 (`1aeaa02`): Important quality finding fixed (README STE hard count 36 → 38 → 36); re-review pass/approved, no findings.

- Task 3.1 — round 1 (`d7c60d8`): plan Verify/SC-27 aligned to DC2 by the controller (`7970c19`); extractor shows paths past the cut, marks subagent calls, skips bad lines; logs re-extracted from saved streams. Re-review pass/approved, two Minors (above).
- Task 3.2 — reviewed pass/approved (Minors above). SC-30 carried to Task 5.1.
- Task 4.1 — round 1 (`d4d7507`): rewrite widened to the whole `skills/diagnosing-bugs/` prefix (DC1). Re-review pass/approved, no findings.

## Final review chain

- Correctness review at `f27c305`: blocking L1, L4, L5 (75); L2 (50) fixed with them in `168345c`. Re-score: all four fixed; new N1 (40) and D-b (55, a #308 deletion that did not survive) fixed in `a411aa9`. Advisory, not fixed: L3, L6, L7, L8, N2. Full table: SUMMARY `### Correctness Review`.
- Intent review at `f27c305`: 8 findings, none blocking. #4 = L1; #8 recorded in prose (whole suite is not a Verify row). Full table: SUMMARY `### Intent Findings`.

## Harness-Delta

- backlog (Task 1.1): in a worktree-isolated session the sandbox refuses compound shell lines, `cd`-prefixed lines and `$?` chains, so each check runs as its own call. The implementer brief could say so up front.
