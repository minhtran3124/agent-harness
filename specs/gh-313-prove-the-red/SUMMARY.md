# gh-313-prove-the-red — Summary

Lane: high-risk
Confidence: high
Reason: four risk flags (existing behavior, public contracts, weak proof, cross-platform); no manifest hard gate fires on the expected paths
Flags: existing behavior, public contracts, weak proof, cross-platform
Affects: scripts/verify_summary.py lane mode (the evidence authority read by hooks/commit-gate.sh check_lane_evidence and deployed to consumers)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no
<!-- Optional Codex diagnosis metadata is an all-or-nothing pair:
     Runtime-mode and Runtime-evidence-id. Add it only from codex_harness_doctor.py. -->

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<!-- The user's request VERBATIM at intake — do NOT paraphrase or summarize. Either form:
     the chat request verbatim (legacy slugs), or the line
     `Intent-source: specs/<slug>/intent.md @ <sha>` followed by the request verbatim: the
     intent's `## Original request`, else the chat request, else `none — intent.md is the request`.
     This is the oracle for intent-review (the final stage of subagent-driven-development):
     the third reviewer is blind to PLAN.md and checks the finished diff against this text
     (plus the pinned intent.md, when present). If the request came over several
     conversational turns, quote the scope-deciding sentences in chronological order.
     Capturing intent here, not in the plan, is what keeps the intent oracle independent of
     the plan oracle. -->

Intent-source: specs/gh-313-prove-the-red/intent.md @ 11ac08f97c0606e1abd05d5e26f3c3a21310233e

GitHub issue #313 step 1 only (prove the red): in scripts/verify_summary.py --lane bug-fix branch, require a non-empty `git diff <red sha>..HEAD` in the changed code, keep REQUIRE_RED_TEST=1 advisory-by-default switch. Step 2 (routing to diagnosing-bugs) is out of scope until #318 exists. Worktree .claude/worktrees/feat+gh-313-prove-the-red (branch feat/gh-313-prove-the-red from sdlc ece206d). PR base: sdlc. Open point for the user: which diff counts — (a) any diff after <red sha> excluding specs/ and test files, or (b) a new field naming the fixed files.

Issue #313 step 1 text: "Prove the red. `scripts/run_at_commit.py` takes one rev and one command, and it does not know red from green. So put the assertion in the bug-fix branch of `scripts/verify_summary.py --lane`, which already parses the `red` row and its `<red sha>`. Require a non-empty `git diff <red sha>..HEAD` in the files that the row names. Keep the `REQUIRE_RED_TEST=1` switch: advisory by default, blocking when set." Proof: "Create a canary spec with a no-op \"fix\". Run `verify_summary.py --lane` on it. The issue passes when the command exits with code 1. Record the run in the SUMMARY."

### Intake notes

<!-- Agent-written intake notes (confidence reasoning, assumed defaults, re-pin lines).
     Not part of the intent oracle. `- none` when empty. -->

- Confidence high: the user approved the draft on 2026-10-17 with both proposals: open question 1
  is option (a) (any diff outside `specs/**` and the red row's test files), and an unresolvable
  `<red sha>` is an advisory that blocks under `REQUIRE_RED_TEST=1`.
- Input-type is `harness improvement`, not `bug fix`: the current check works as its docstring
  states ("Does not verify: ... that the test exercises the bug"); this adds a capability.
- Worktree `.claude/worktrees/feat+gh-313-prove-the-red` cut from `sdlc` `ece206d`; PR base `sdlc`.
- Observed at intake: `hooks/commit-gate.sh` `check_lane_evidence` runs `--lane` on a temp copy
  of the staged SUMMARY, so the new check cannot locate the repo from the SUMMARY path; it must
  use the process cwd's repo. Issue #313 step 2 stays out of scope (waits for #318).

## What changed

For a bug-fix SUMMARY, `scripts/verify_summary.py --lane` now checks that code changed after the
red commit. For each matched red/green pair it compares the red commit with the git index of the
current repo (`git diff --cached --name-only -z --no-renames`), drops `specs/` paths and the paths
named in the red test command, and reports `no code change` when nothing is left, or
`cannot check the fix diff` with a cause when git, the repo or the commit is missing. Both are
advisories by default and errors under `REQUIRE_RED_TEST=1`. `rules/auto-correct-scope.md` and
the implementer prompt each state the new requirement in one sentence.

### Rationale

The existing red/green check reads only SUMMARY text, so a no-op fix passed. The check lives in
`verify_summary.py`, the evidence authority that the commit gate and manual `--lane` runs share,
and reads the index because the gate judges the staged tree (design D1–D9, user decisions intent
Q1 = a, Q2, round-1 Q1–Q5, approach A).

### Alternatives considered

- An `--expect-red` mode in `run_at_commit.py`: rejected, it does not know red from green and a
  test run does not prove that code changed.
- A bash check in `hooks/commit-gate.sh`: rejected, it edits a high-blast hook and a manual
  `--lane` run would miss it.
- A new `Fix-files:` SUMMARY field (intent Q1 option b): rejected by the user for option (a).

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| canary: no-op fix | `python3 -m pytest -q scripts/test_verify_summary.py -k fix_diff_noop` | 0 | 1 passed; `--lane` exits 1 under `REQUIRE_RED_TEST=1` and prints a `!` `no code change` advisory without it; run with `/tmp/harness-tests-venv/bin/python` (system python3 has no pytest) | SC-1 |
| real fix passes | `python3 -m pytest -q scripts/test_verify_summary.py -k fix_diff_real_fix` | 0 | 1 passed | SC-2 |
| fix-diff cases | `python3 -m pytest -q scripts/test_verify_summary.py -k fix_diff` | 0 | 12 passed | SC-3 |
| commit-gate shape | `python3 -m pytest -q scripts/test_verify_summary.py -k fix_diff_commit_gate_shape` | 0 | 1 passed | SC-4 |
| gh-302 regression | `python3 -m pytest -q -rs scripts/test_verify_summary.py -k fix_diff_gh302` | 0 | 1 passed, no skip | SC-5 |
| existing red/green | `python3 -m pytest -q scripts/test_verify_summary.py -k RedGreen` | 0 | 19 passed | SC-6 |
| rule clause | `grep -q "and the red test files" rules/auto-correct-scope.md` | 0 | | SC-7 |
| prompt clause | `grep -q "and the red test files" skills/subagent-driven-development/implementer-prompt.md` | 0 | | SC-8 |
| STE baseline | `python3 scripts/check_ste_baseline.py --strict --against ece206d` | 0 | 0 above baseline | SC-9 |
| phrase pins | `python3 scripts/check_task_review_contract.py` | 0 | passed | SC-10 |
| plan contract | `python3 scripts/check_plan_contract.py specs/gh-313-prove-the-red/PLAN.md` | 0 | passed | SC-11 |

### Not auto-verified

- The new implementer-prompt sentence meets the STE limits — reached traceability; `ste-lint`
  does not read fenced prompt prose, so it was checked by hand (13 words, active, no semicolon).
- Git behavior on the macOS CI runner matches git 2.43.0 — reached provenance (local runs only);
  CI re-runs the suite on macOS.
- A fix-diff pass proves that a non-test path changed, not that the change fixes the bug — by
  design (provenance tier; see design "What we do not claim").

### Rollback

- `git revert 6572584 579eb28` (the code check and the prose clauses); no data or state to undo.
  Until reverted, `REQUIRE_RED_TEST` unset keeps the check advisory.

### Harness-Delta

- none

### Task review notes

- Task 1.1 Minor: six fix-diff tests call `_red_fix_diff_issue` directly, not the plan's declared
  `main(["--lane", ...])` seam; the design's Tests section names `_red_fix_diff_issue` as a seam,
  and the CLI wiring is covered by six other tests. Forwarded to final review.
- Task 1.1 Minor: `_git` strips its output, so a diff path that starts or ends with a space would
  not match its token. Forwarded to final review.
- Task 1.2: no findings.
