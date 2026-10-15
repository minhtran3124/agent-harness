# failing-test-first — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate (edits skills/feature-intake and skills/subagent-driven-development); also changes scripts/verify_summary.py, which decides what every other gate accepts as evidence
Flags: existing behavior, weak proof, multi-domain
Affects: scripts/verify_summary.py (lane-evidence check relayed by hooks/commit-gate.sh), skills/feature-intake, skills/subagent-driven-development
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/failing-test-first/intent.md @ c88ce16620ca097b2a8457ba10acf39a563c3d21

"what next item for sdlc?" — then, after I recommended E5 and asked "Should I start E5
(failing-test-first for bug fixes)? I'd begin with `feature-intake` on a new branch cut from
`sdlc`.", the reply: "yes"

E5 as written in `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §6:
"**Failing-test-first protocol for bug fixes**: when `Input-type` is a bug fix, the `### Verify`
table must contain a red row (test fails before fix, with commit sha) and a green row after" —
Where: `skills/feature-intake`, `skills/subagent-driven-development`, `scripts/verify_summary.py`
(advisory first).

### Intake notes

- intent.md drafted from chat and approved by the user ("approve") on 2026-10-15; committed as c88ce16.
- Confidence is high: E5 has one reading. Q1–Q3 in intent.md are design choices with assumed defaults, settled in brainstorming.
- Branch `feat/failing-test-first` cut from `sdlc` (8d6b082); the PR targets `sdlc`.
- Escalate: no. The workflow-engine hard gate is the reason for the lane; the user approved the scope in intent.md, so no further narrowing is needed.

## What changed

A bug-fix run can now prove its test failed before the fix. Intake has a `bug fix` input type. A
new helper, `scripts/run_at_commit.py <sha> -- <test command>`, runs a test in a temporary
detached worktree at the pre-fix commit and returns its exit (125 for its own failure, 124 on its
50 s timeout, 128+n on a signal). `scripts/verify_summary.py` checks that a bug-fix SUMMARY's
`### Verify` holds a `red` row (the helper at the red sha, exit 1–123) and a `green` row (the same
test command, exit 0), or a `Red test exempt: <reason>` line. The check is advisory by default
and blocks under `REQUIRE_RED_TEST=1`; each advisory now prints its own enforcing variable. The
implementer prompt receives the run's input type and the red/green steps, the lane-evidence rule
names the row shape for any lane, and the helper ships to consumer repos.

### Rationale

Every `### Verify` row is re-run by `verify_summary.py --check`, which fails on a claimed/actual
exit mismatch and otherwise rewrites the Exit cell. A plain red row (the test at HEAD, exit 1)
therefore breaks after the fix. Running the red test at the pre-fix commit makes both rows
reproduce their claimed exit on every re-run, so the evidence fits the existing re-run machinery
instead of needing an exemption from it (design D1, approved by the user 2026-10-15).

### Alternatives considered

- A separate `### Red test` section outside `### Verify` — simpler, but the red evidence becomes
  an unchecked claim and departs from E5's wording. Rejected by the user.
- A plain red row with `--check` skipping rows marked `red` — no new script, but it exempts one row
  class from the re-run every other row gets. Raised by the design reviewer; rejected; shown to
  the user before design approval.

### Deviations

- Context-propagation audit repair (`9ec0e59`), outside the plan's Files list: `skills/subagent-driven-development/SKILL.md` now fills `[INPUT_TYPE]` like `[LANE]`, so the implementer can see that a run is a bug fix; the rule names the red-row command; a drift test anchors both prose copies to the checker.
- Rule 3 — the audit repair took `skills/subagent-driven-development/SKILL.md` to 602 words, over the 600-word ceiling that `scripts/test_audit_skill_prompts.py` enforces; the two placeholders are now written as one token (`[LANE]`/`[INPUT_TYPE]`). A first rewording broke `tests/scripts/sdd-artifact-handoffs.test.sh`, which pins "the controller writes it verbatim to", and was reverted before commit. Commit `32c5978`; the receipt was re-reviewed at this head.
- Rule 2 — `scripts/run_at_commit.py` also requires `--` to be exactly the second argument (one revision before it); any other position exits 125 with the usage message. It narrows the `<rev> -- <arg>...` interface to the shape the design names. Commit `04392a6`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| helper tests | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_run_at_commit.py` | 0 | 9 passed | SC-1 |
| helper unknown sha | `python3 scripts/run_at_commit.py 0000000 -- python3 -c pass` | 125 | prints `run_at_commit: unknown commit '0000000'` | SC-2 |
| helper passes exit through | `python3 scripts/run_at_commit.py HEAD -- python3 -c "raise SystemExit(3)"` | 3 | runs in a temporary worktree at HEAD | SC-3 |
| red/green cases | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_verify_summary.py -k red_green` | 0 | 19 passed | SC-4 |
| verify_summary tests | `env PATH=/tmp/harness-tests-venv/bin:/usr/bin:/bin python3 -m pytest -q scripts/test_verify_summary.py` | 0 | 91 passed (72 before + 19) | SC-5 |
| template input type | `grep -q 'bug fix' templates/SUMMARY.template.md` | 0 | | SC-6 |
| intake input type | `grep -q 'bug fix' skills/feature-intake/SKILL.md` | 0 | | SC-7 |
| implementer instruction | `grep -q run_at_commit.py skills/subagent-driven-development/implementer-prompt.md` | 0 | | SC-8 |
| lane-evidence rule | `grep -q REQUIRE_RED_TEST rules/auto-correct-scope.md` | 0 | | SC-9 |
| consumer deploy | `bash tests/scripts/consumer-subset.test.sh` | 0 | 19 passed; exits 1 with the `CONSUMER_SCRIPTS` entry removed (checked once, restored) | SC-10 |

### Not auto-verified

- The red/green check proves a red row's test failed on the bug — reached traceability only. The
  check reads the row's format; where `--check` re-runs it (finishing, CI, `REQUIRE_VERIFY=1`), the
  re-run proves only that the pre-fix commit returns the same non-zero exit. A collection or setup
  failure gives that too (advisory finding, design "What we do not claim").
- The green test exercises the bug — not checked by any gate; left to task and correctness review.
- Bug fixes are labelled `Input-type: bug fix` — not checked; intake classifies by judgment.
- The helper's process-group kill and `start_new_session` behave the same on macOS — reached
  truth on Linux only (`scripts/test_run_at_commit.py`); macOS runs only in CI.
- No real bug-fix run has used the protocol end to end yet; the red/green path is proven by unit
  tests on synthetic SUMMARYs only.

### Rollback

- Revert the PR's merge commit on `sdlc`: `git revert -m 1 <merge sha>`. No data, state or hook
  change to undo; consumer repos drop `.claude/scripts/run_at_commit.py` on their next re-sync
  (the deploy prunes files no longer listed).

### Context-Propagation Audit

Diff `c88ce16..9ec0e59`. Consumers found with `grep -rn` over `skills/`, `rules/`, `agents/`,
`scripts/`, `hooks/`, `templates/` and `tests/` for `bug fix`, `run_at_commit`, `REQUIRE_RED_TEST`,
`[LANE]` and `Input-type`; each row below was confirmed by reading the named file.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `skills/feature-intake/SKILL.md` step 2 (`bug fix` input type) | intake | main session | skill body loaded on invocation | `skills/feature-intake/SKILL.md:26-27` |
| `templates/SUMMARY.template.md` (`bug fix` option) | intake writing SUMMARY | main session | template read at intake step 6 | `skills/feature-intake/SKILL.md` step 6 names the template |
| `implementer-prompt.md` red/green step | implementer | fresh subagent | pasted (the controller fills the fenced prompt) | `skills/subagent-driven-development/SKILL.md:52-53` |
| Bug-fix trigger (`Input-type`) for that step | implementer | fresh subagent | pasted `[INPUT_TYPE]`, filled from SUMMARY like `[LANE]` | **FAIL → repaired in 9ec0e59.** Before: the brief (`task_brief.py`) and prompt carried no Input-type, so the child could not see the condition. Test `test_red_green_input_type_reaches_the_implementer` |
| `rules/auto-correct-scope.md` bug-fix bullet | intake (any lane, incl. tiny with no implementer) | main session | explicit Read at intake step 1 | `skills/feature-intake/SKILL.md` step 1 |
| Same bullet | implementer | fresh subagent | explicit Read ("FIRST: Read `rules/auto-correct-scope.md`") | `implementer-prompt.md` Auto-Correction Scope section |
| Red-row command shape for a tiny-lane bug fix | main session | main session | the rule bullet above | **FAIL → repaired in 9ec0e59.** Before: the bullet named the requirement but not the `run_at_commit.py` command |
| Red-row command shape (inline copies in the prompt and the rule) | implementer, main session | both | pasted / explicit Read | **FAIL → repaired in 9ec0e59** (inline subset with no anchor). Now pinned by `test_red_green_prose_command_shape_is_accepted_by_the_check`; a mutation of the rule's command made it fail |
| `verify_summary.py` red/green warning | agent at commit time | main session or implementer | `hooks/commit-gate.sh:289` relays `!` lines from a passing `--lane` run | test `test_red_green_missing_red_row_warns` (the printed line starts with `!`) |
| `run_at_commit.py` path in derived prose | consumer repo agents | any | deploy rewrites `scripts/` to `.claude/scripts/` for `CONSUMER_SCRIPTS` entries | `tests/scripts/consumer-subset.test.sh` "every .claude/scripts/ path named in derived Markdown actually resolves" (19 passed) |

Result: **PASS** after repair. Three rows failed at `087f331` and were repaired in `9ec0e59`; STE
hard counts did not rise (auto-correct-scope 0→0, SDD SKILL 1→1, implementer-prompt 0→0).

### Advisory Findings

Correctness review of `c88ce16..9ec0e59`: six FIND angles (removed-behavior reported none), 8
locations after dedupe, each scored in a fresh context. All scored 50 (real but minor or rare),
below the threshold of 75, so none entered the fix loop. All are Rule 1–3 class.

- `scripts/run_at_commit.py` `main` (score 50) — only `HelperError` is caught. An `OSError` from
  `tempfile.mkdtemp` (bad `TMPDIR`), `git` missing from `PATH`, or non-UTF-8 git output exits 1
  with a traceback instead of 125, and 1 is a valid red exit. Fix: catch `Exception` around the
  body and return 125.
- `scripts/run_at_commit.py:26` (score 50) — the 50 s budget covers only the test, not worktree
  setup and cleanup. If `run_checks`' outer timeout fires first (`--timeout` below 50, or slow
  setup plus a test near 50 s), SIGKILL skips `finally`: the temporary worktree stays registered
  and the test process group is orphaned. Fix: one deadline for the whole helper, below the
  caller's, and cleanup on SIGTERM.
- `scripts/run_at_commit.py` `_run` (score 50) — Ctrl-C or SIGTERM to the helper does not kill
  the test's process group; on Ctrl-C the worktree is removed under a running test. Fix: kill the
  group on any exit path.
- `scripts/run_at_commit.py:73` (score 50) — the repo-wide `git worktree prune` can delete the
  admin records of another unlocked worktree whose directory is temporarily absent. Fix: drop
  it; `finally` already removes the helper's own worktree.
- `scripts/verify_summary.py:413` (score 50) — `Input-type` must equal `bug fix` exactly, so
  `bug-fix`, `bugfix` or `bug fix (harness)` skip the check silently, even under
  `REQUIRE_RED_TEST=1`. Fix: match a leading `bug[ -]?fix` token.
- `scripts/verify_summary.py:445` (score 50) — the literal placeholder `Red test exempt: <reason>`
  counts as a real exemption. Fix: reject a reason that `_is_placeholder` matches.
- `scripts/verify_summary.py:429-433` (score 50) — the 1–123 red range accepts exits where the
  test never ran (pytest 2, 4, 5; an ImportError's 1). Already named in design "What we do not
  claim"; rejecting pytest's 2/4/5 would be runner-specific.
- `scripts/verify_summary.py:400` (score 50) — `REQUIRE_RED_TEST=False`, `no` or `off` turn
  blocking on; copies the existing `_not_auto_verified_is_blocking` convention and fails closed.

Task-review Minor findings forwarded to this review: `scripts/test_run_at_commit.py:242-250` (the
absolute-path test cannot detect a helper that resolves the repo from `__file__`; covered by the
in-process test); `test_red_green_green_command_differs_is_rejected` asserts only
`"green" in issue`; `_RED_COMMAND_RE` accepts any path ending in `scripts/run_at_commit.py`, wider
than the design's `scripts/` or `.claude/scripts/`. The implementer-prompt exit-range Minor was
fixed in `9ec0e59`.

### Intent Findings

Intent review of `c88ce16..9ec0e59` (plan-blind): no gap; SC-1 to SC-10 each proven by a Verify
row. Three report-only or advisory findings:

- excess (report-only) — the new public helper `scripts/run_at_commit.py`, shipped to consumers.
  No intent clause names a helper; it is the mechanism of approach A, which the user approved
  explicitly (design D1). Kept.
- drift, behaviorally different within design latitude (advisory) — a red row must use the helper
  command shape with exit 1–123; a plain test command with the sha in Notes (intent Q3's first
  option) is rejected. Intent Q3 left the marker to design; the user approved D1/D5/D7.
- drift, equivalent (advisory) — intake step 2 adds guidance: "Use `bug fix` for any fix of wrong
  behavior, harness bugs included." The intent asked only for the value.

### Harness-Delta

- backlog — `docs/solutions/harness/test-and-doc-lint-gate-scope.md` (confirmed 2026-07-17) still
  says new tests must be added to a hand-written `PYTESTS` list; `scripts/run-tests.sh` now
  collects `test_*.py` with `find`. Route to `compound`.
- fix-direct — `task_brief.py` and the implementer prompt carried the lane but not the input type,
  so a condition on the run's type could not reach the implementer. Fixed in `9ec0e59` with
  `[INPUT_TYPE]`.
