# gh-312 canary and gh-175 replay

Both runs dispatched the `task-reviewer` agent with the task-reviewer prompt at commit `113a374`
(the seam check from Task 1.3). The reviewer was not told which tests were bad.

## Canary (SC-5, pass criterion)

Fixture: `canary/PLAN.md` (marker plan, one task, seam "`word_count()` return value"),
`canary/brief.md` (built by `task_brief.py`), `canary/package.md` (a hand-written fixture diff)
and `canary/report.md`. The diff adds four tests:

| Test | Planted defect | Expected verdict |
|---|---|---|
| `test_word_count_simple` | none (literal 3 at the seam) | no finding |
| `test_tokens_drop_empty_parts` | off-seam: tests the private `_tokens` | Important |
| `test_word_count_sample` | expected value computed by the code under test (`len(wc._tokens(SAMPLE))`) | Important |
| `test_word_count_empty` | none (literal 0 at the seam) | no finding |

The fixture also holds an unplanted-for-scoring real bug: `_tokens` splits on `" "` only, so a tab
does not separate words. The circular test hides it.

Reviewer output, run 1:

```yaml
spec_verdict: pass
quality_verdict: needs_fixes
meaning: []
findings:
  - severity: Important
    category: quality
    location: canary/test_wc.py:14-16 (package.md diff lines 54-56)
    rationale: The expected value is copied from the implementation's own output. `test_word_count_sample` does `expected = len(wc._tokens(SAMPLE))` and then asserts `wc.word_count(SAMPLE) == expected`. Since `word_count` is just `len(_tokens(text))`, the assertion is always true and cannot catch a wrong count for spacing, which is the failure the declared seam is meant to catch. This test also hides a real behavior: `_tokens` splits only on " ", so the tab in SAMPLE ("fox\tjumps") is counted as one word. The test would pass whether the answer is 4 or 5.
    action: Replace `expected` with a hand-derived literal. First decide whether tabs and newlines separate words (see the Minor finding below), then assert that literal value.
    checked_against: SC-1
  - severity: Important
    category: quality
    location: canary/test_wc.py:10-11 (package.md diff lines 50-51)
    rationale: The brief has `Plan-contract: 2`, and its only declared seam is "`word_count()` return value". `test_tokens_drop_empty_parts` tests the private helper `wc._tokens`, not that seam. It ties the tests to internal structure rather than to the declared contract.
    action: Remove this test, or rewrite it to assert through `word_count()`, for example `word_count("a  b") == 2`.
    checked_against: none
  - severity: Minor
    category: spec
    location: canary/wc.py:4-5 (package.md diff lines 28-29)
    rationale: The brief defines a word as "a run of non-space characters". This has two readings. One is that only U+0020 separates words, which is what `text.split(" ")` implements. The other is that any whitespace separates words, which `text.split()` would implement. Under the second reading, "a\tb" and "a\nb" each count as 1 instead of 2. SC-1 ("a b  c") passes under both readings, so this is not a blocking spec failure. The ambiguity is not stated anywhere, and the circular sample test (first finding) keeps it from showing up.
    action: Have the controller or plan author confirm which reading is intended. Then add a test with a literal expected value for tab or newline input.
    checked_against: SC-1
search_surface:
  - specs/gh-312-test-seams/canary/brief.md (Files list, Seams, Plan-contract 2, SC-1)
  - specs/gh-312-test-seams/canary/report.md (status DONE, no fix rounds)
  - specs/gh-312-test-seams/canary/package.md (diff stat and diff)
  - rules/review-policy.md
  - "Seam step 3, one focused search: Glob `**/canary/**`; no corpus of real text inputs and no word_count callers."
```

Both planted defects got an Important finding. Neither clean test got a finding. The reviewer
also surfaced the hidden tab bug through the circular test.

Canary result: pass

## gh-175 replay (SC-6, evidence only)

Fixture: `canary/replay-175/PLAN.md` is the gh-175 plan at `e76b0fe` with two lines added after
the fact: the `- Plan-contract: 2` marker and a `Seams:` line for Task 2.1 ("`runtime/resume_decision.py
--slug <slug>` JSON output — catches: a wrong action, reason_code, next_task or claimed_complete
for a given PLAN, SUMMARY and RUN.json; misses: crashes in git or file I/O that the CLI turns into
exit 3"). The brief comes from `task_brief.py`; the package is `review_package.py` over
`e791638^..e791638`, the Task 2.1 commit (2 files, 1392 insertions). The original implementer
report was not preserved; `canary/replay-175/report.md` says so.

Limit: the reviewer ran against today's working tree, which holds more real `specs/*` runs (it
found 32 `RUN.json` files) than existed on 2026-08-09. Real plans and Status Logs did exist then
(the gh-175 correctness review reproduced its bugs against them), so the step-3 finding does not
depend on the extra runs.

Reviewer output, run 1 (verdicts, severities and locations verbatim; rationales and actions
shortened, except the seam step-3 rationale, which is verbatim):

```yaml
spec_verdict: fail
quality_verdict: needs_fixes
meaning: []
findings:
  - severity: Important
    category: spec
    location: runtime/test_resume_decision.py:941-996
    rationale: The state matrix runs every FSM state against one active markdown plan only. The proposed-plan path, the plan-unknown-status stop, the untracked run with a missing or shipped plan, and catch-up with a paused or proposed plan are untested.
    action: Parametrize the matrix over plan status and format for the execution states and the untracked status.
    checked_against: SC-2
  - severity: Important
    category: spec
    location: runtime/resume_decision.py:712-764
    rationale: No test combines a cursor conflict with a terminal, wait, interrupt, repair or verifying state, so a decision-precedence regression would pass the suite.
    action: Add conflict-plus-lifecycle tests and assert the lifecycle route stays unchanged.
    checked_against: SC-3
  - severity: Important
    category: quality
    location: runtime/test_resume_decision.py:1371-1380
    rationale: Test-seam step 1. The parity test calls the internal `decision.parse_tasks(body)` directly, not the declared seam (CLI JSON / `decide()` output).
    action: Assert parity through the seam, or declare `parse_tasks` as a seam in the plan.
    checked_against: SC-5
  - severity: Important
    category: quality
    location: runtime/test_resume_decision.py:829-848, 1205-1227
    rationale: Test-seam step 3. Every test builds its PLAN from the synthetic `_ACTIVE_MD_PLAN` or `_XML_PLAN` and its run from `init_to`. Real inputs of the seam's shape exist (Glob `specs/*/RUN.json` returned 32 real run directories, each with a real PLAN.md and Status Log). The per-mention completion parser and the renderer parity claim are exactly the logic that real Status Log prose would stress - multi-task entries, markers before the mention, backticked SHAs.
    action: Add at least one test that copies a real `specs/<slug>/` into tmp_path and asserts decide()'s task_ids against render_plan and its claimed_complete against the known history.
    checked_against: SC-5
  - severity: Minor
    category: quality
    location: runtime/resume_decision.py:227-240
    rationale: parse_status_completion collects every backticked SHA in the whole entry and attaches all of them to every task the entry claims complete; completion is per mention but commit association is per entry.
    action: Extract SHAs per mention segment and add a two-task, two-SHA test.
    checked_against: SC-5
  - severity: Minor
    category: quality
    location: runtime/test_resume_decision.py:1526-1535
    rationale: The read-only byte snapshot omits SUMMARY.md, STATE.md and the git-evidence path.
    action: Add them to the snapshot.
    checked_against: SC-7
  - severity: Minor
    category: quality
    location: runtime/resume_decision.py:618
    rationale: A future STATE `Updated:` date gives negative days and is accepted as fresh.
    action: Treat a future date as stale or unparseable.
    checked_against: SC-6
  - severity: Minor
    category: quality
    location: runtime/test_resume_decision.py:941-959
    rationale: Test-seam step 2 unresolved; the reason_code strings in EXPECT match the implementation and the package holds no independent source for them.
    action: Cite the design's reason-code table in the test module.
    checked_against: SC-2
search_surface:
  - specs/gh-312-test-seams/canary/replay-175/{brief.md,report.md,package.md}
  - rules/review-policy.md
  - "Grep reason codes in canary/replay-175/ excluding package.md: no matches"
  - "Seam search: Glob specs/*/RUN.json returned 32 real run directories"
```

Comparison with what the gh-175 correctness review found later
(`specs/gh-175-executable-resume-cursor/SUMMARY.md:110`):

| Replay finding | gh-175 correctness finding | Match |
|---|---|---|
| Important, seam step 3: synthetic-only fixtures; test on a real `specs/<slug>/` and assert parity with the renderer | [A/B] parser parity failed on a real plan (render 7 tasks, resume 0); [C] Status-Log parser disagreed with the renderer on ~31 of ~49 real plans. The ship fix was the corpus tests `test_corpus_parity_parse_tasks_matches_render_plan` and `test_corpus_completion_never_over_claims_vs_render` | yes: the same fixture-fitting cause and the same remedy |
| Minor: SHAs collected per entry, not per mention | [C] "SHAs collected entry-wide" | yes: same defect |
| Important, seam step 1: parity test calls `parse_tasks` directly | none directly | partial: the off-seam test is the one that asserted parity on the synthetic fixture only |
| Important, spec: plan-status matrix gaps; Important, spec: precedence untested | [D], [F], [O], [G], [I], [J], [L], [H] are code defects in other branches | no direct match |
| Minor: future STATE date accepted | none | new |

The original per-task review of gh-175 Task 2.1 approved this diff. With the seam check, the
reviewer returned `needs_fixes` and named the fixture-fitting cause that the plan-blind
correctness review later confirmed through reproduced bugs.

Replay result: the reviewer flagged the synthetic-only fixtures (Important, seam step 3) and the per-entry SHA association (Minor), which match gh-175 correctness findings [A/B] and [C]; it did not reproduce the other nine findings, which are code defects outside the test-seam check
