# gh-258-sc-goalpost-guard — Summary

Lane: high-risk
Confidence: medium
Reason: changes scripts/verify_summary.py, the script that decides what every other gate accepts as evidence (CI warn tier for scripts/), adding a new warn-first gate over branch history; #258 itself names it a separate high-risk-lane change; flags existing behavior, weak proof, multi-domain
Flags: existing behavior, weak proof, multi-domain, new gate
Affects: scripts/verify_summary.py (evidence authority for commit-gate lane check, ci-strict-gate, finishing), SUMMARY.md / PLAN.md SC contract
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Scope-deciding sentences, in chronological order:

> check issue https://github.com/minhtran3124/agent-harness/issues/258, xem thu da implement het cac item trong table rollout chua?

> merged. start item 5 tiep theo

Item 5 of GitHub issue #258 (https://github.com/minhtran3124/agent-harness/issues/258), as written in the issue:

> **Purpose.** It stops a failing acceptance check from being quietly weakened until it passes.
>
> **Gap in our harness.** The `weakening-validation` signal is warn-mode and diff-based. Nothing ties a changed `SC-n` `Expected` value to the run where that row failed.
>
> **Target.** `scripts/verify_summary.py` warns when an `SC-n` row's `Check` or `Expected` changes in the same branch where that row is recorded as failing, unless `### Deviations` has an entry that names the row. Warn-first, the same rollout pattern as `weakening-validation`. Separate high-risk-lane change.

Items 6 and 7 of #258 are out of scope for this spec. The branch is cut from `spec-format`; the PR targets `--base spec-format`.

Confidence is `medium`, not `high`: the target is written in #258, but two details have a
documented default rather than a single reading, to be settled in brainstorming. (a) What
"recorded as failing" means: the default is that some commit in the branch (`merge-base..HEAD`)
has a `SUMMARY.md` `### Verify` row whose `Criterion` is that `SC-n` with a non-zero `Exit`
(or an `Exit` that differs from the row's `Expected`). (b) Where and when the warning runs: the
default is a `verify_summary.py` mode that needs a base ref, called where `--check` already runs
(the finish flow and `ci-strict-gate.sh`), warn-first with an env flag to block.

## What changed

`scripts/verify_summary.py --sc-history <slug> --base <ref>` walks the branch history (`merge-base..HEAD`) of a spec. It finds each Success Criterion that a committed `### Verify` row recorded as failing: a row with `Criterion` SC-n whose `Exit` differs from that SC's expected exit, judged only where that row was new or changed (D9). It then reports `SC-GOALPOST [SC-n] changed|removed after it failed at <sha>` when the SC's `Check` or expected exit was later changed, or the SC was removed, unless a `### Deviations` heading names SC-n.

The check warns by default (exit 0). With `REQUIRE_SC_STABLE=1` it exits 1 on a finding, and on a usage, git or unexpected error it exits 2. It runs in two places:
- **`scripts/ci-strict-gate.sh`:** a new section runs it for every slug whose PLAN or SUMMARY changed. It sits before the gate's early exit, never exits 0 itself, and reports renamed spec directories as errors.
- **Finish skill, step 3:** it runs there too, against committed state.

### Rationale

Of the readings settled in brainstorming, branch history is the one that matches the issue's wording ("the same branch where that row is recorded as failing"). It needs no new artifact, and it uses evidence that already exists: `verify_summary.py`'s rewrite mode writes the real exits into committed Verify rows. Blocking is an env flag inside `verify_summary.py`, not a manifest mode or a hook, so the CI-pinned 2-warn/7-block gate parity and `hooks/` are untouched.

### Alternatives considered

- Flag any change to an already-committed SC row: rejected, because it flags ordinary SC edits made during plan review.
- A separate failure ledger written by `verify_summary.py`: rejected, because it adds an artifact and a write path that the same agent can edit.
- Read the block/warn mode from `harness-manifest.json`, like `weakening-validation`: rejected, because it changes the CI-pinned gate parity and the hook defaults (high-blast).
- A new category in `hooks/commit-gate.sh`: rejected, because it is high-blast and leaves `verify_summary.py`.

### Deviations

- Decision change: design `DC1` reopens D1 (failure record only at a commit where SUMMARY.md changed, D8), and `DC2` reopens D8 (only where that **row** is new or changed, D9). Both were approved by the user in the correctness fix round ("Sửa #1–#6"), and DC2 completes finding #1.
- Fix round `fb0657f` (Rule 1–2, user-chosen):
  - D8 failure record;
  - `REQUIRE_SC_STABLE` whitespace stripped in the gate to match the script;
  - suppression searches every `Deviations` heading (`_all_sections`);
  - finish step 3 says the check reads committed state only and reports exits other than 0/1;
  - spec-directory rename reported as an error;
  - unexpected exceptions exit 2 instead of a traceback with exit 1.
- Follow-up `2d2525e` (Rule 1): row-level failure record (D9), and per-commit rename detection (a spec created then renamed on the branch). Both were found by the independent re-check.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| intake lane record | `python3 .claude/scripts/verify_summary.py --lane gh-258-sc-goalpost-guard` | 0 | | |
| --sc-history output and exits match the error-behavior table | `python3 -m pytest scripts/test_verify_summary_sc_history.py -q` | 0 | 41 passed after the fix rounds (shared venv first on PATH locally; CI installs pytest on python3) | SC-1 |
| ci-strict-gate SC-history section, old and new cases | `bash tests/scripts/ci-strict-gate.test.sh` | 0 | 47 passed: 35 existing + (j)–(m), (n) REQUIRE whitespace, (o) rename, (p) create-then-rename | SC-2 |
| finish skill runs the history check | `bash tests/scripts/finishing-branch-contract.test.sh` | 0 | 7 passed | SC-3 |
| existing verify_summary modes unchanged | `python3 -m pytest scripts/test_verify_summary.py -q` | 0 | 72 passed | SC-4 |
| finish skill within the 600-word ceiling | `python3 scripts/audit_skill_prompts.py` | 0 | finish skill 584 words | SC-5 |

The full suite is not a Verify row (`rules/plan-format.md` Guardrail 4). `bash scripts/run-tests.sh` reported 877 passed, ALL GREEN, at `2d2525e` (implementer run, 2026-10-09); the controller re-runs it at finish.

### Correctness Review

The six FIND angles ran over `51eb4e0..dcdce4d` and produced 7 locations after dedup, each scored once by an independent scorer against a threshold of 75. None reached 75:
- the failure-record definition, the REQUIRE whitespace mismatch, the first-Deviations-only lookup, the committed-only finish step, and the spec-directory rename each scored 50;
- the crash read as a finding scored 25;
- the escaped `\|` scored 0 (pre-existing, and the lint already rejects it).

The user chose to fix #1–#6 (`fb0657f`). The independent re-check closed 6/6 and found two residual gaps, R1 (confidence 75, reproduced) and R2 (50). Both were completions of approved fixes, and both were fixed in `2d2525e` (D9, per-commit rename). That commit was re-checked again (see below).

Remaining advisories, not fixed:
- R3: with merges, the "previous SUMMARY" is the previous commit in `rev-list` order, not necessarily the parent, so a sibling comparison is possible (re-check confidence 25, rare for spec directories).
- The escaped `\|` cell split (0, pre-existing).
- A rename combined with a heavy rewrite pairs as a delete plus an add and is not detected.
- Final re-check of `2d2525e`: R1 and R2 closed; 8 probes confirmed that real failures (first committed failing, pass→fail, unchanged re-run keeps the first reference) are still recorded. Notes, each at 25, recorded and not fixed:
  - a re-run that still fails but edits only the Notes cell is not judged (D9 excludes Notes by design);
  - a rename introduced only while resolving a merge is not seen (`git log` without `-m`);
  - a delete plus an add of two template-similar specs in one commit can pair as a false rename error;
  - the walk is linearised across merges (same as R3).

### Intent Findings

The intent review (plan-blind) over `51eb4e0..dcdce4d` found no gap. Every clause is met: warns in `verify_summary.py`, branch history, Deviations suppression, warn-first, called from finish and `ci-strict-gate.sh`, its own high-risk change, and items 6 and 7 untouched. The reviewer re-ran SC-1..SC-5 (all exit 0).
- **drift (advisory, equivalent):** the issue's default text mentions "non-zero Exit"; D1/D8/D9 use "differs from the SC's Expected", which is right when an SC expects exit 1.
- **drift (advisory):** `Expected` is compared by its `exit <n>` token only (D6), so rewording the prose after it is not a goalpost move.
- **drift (advisory, equivalent):** the block switch is the env flag `REQUIRE_SC_STABLE`, not a manifest `mode` as for `weakening-validation` (D2). Warn-first still holds.
- **excess (report only):** a `removed` finding kind (D3), traced to the issue's Purpose.
- **drift (advisory, equivalent):** the CI section sits next to the item-3 section, before the tiers, so specs-only PRs are checked.
- The `--base spec-format` PR target is confirmed at PR creation.

### Context-Propagation Audit

**Result: PASS.** Range `51eb4e0..HEAD`. Search surface: `grep -rln "sc-history\|SC_STABLE"` over `adapters/`, `agents/`, `skills/`, `scripts/render_skill_prompt.py` and `scripts/render_codex_adapter.py`. The only hit is `skills/finishing-a-development-branch/SKILL.md`. No isolated prompt or agent definition carries the new instruction.

| Source | Consumer | Context | Delivery | Proof |
| --- | --- | --- | --- | --- |
| `finishing-a-development-branch/SKILL.md` step 3 (`--sc-history` clause) | finish controller | main | the skill body, loaded on invocation | `finishing-branch-contract.test.sh` (6 passed) |
| same | consumer repo finish controller | main | deployed skill, with `scripts/` rewritten to `.claude/scripts/`; `verify_summary.py` already in `CONSUMER_SCRIPTS` | `consumer-subset.test.sh` (17 passed); `lint-doc-truth.sh` exit 0 |
| `scripts/ci-strict-gate.sh` SC-history section | CI `strict-gate` job | CI (harness repo only) | runs on every PR | `ci-strict-gate.test.sh` (47 passed after the fix rounds) |
| isolated prompt contracts (unchanged) | reviewers, scorers | subagent | `CONTEXT_MATRIX` | `render_skill_prompt.py --check-all`: "all contracts present" |

**Advisory:** the Codex plugin ships the skill text whole, so the `scripts/` call in the finish step depends on how the Codex alpha provides helpers. The other finish helpers already have this dependency, and it is unchanged here. Traceability only.

### Minor review findings

- Task 1.1 (`2a47380`): `_run_sc_history` reports any later git failure (`rev-list`, `rev-parse --short`) as "not inside a git repository, or git cannot run". The exit code (2) is correct, but the message names the wrong cause, and `_git` drops git's stderr.
- Task 1.1 (`2a47380`): `test_base_without_sc_history_is_a_usage_error` calls `subprocess.run` directly instead of the env-scrubbing `run()` helper.
- Task 1.1 (`2a47380`): `REQUIRE_SC_STABLE` blocks only on exactly `"1"`, while `REQUIRE_NOT_AUTO_VERIFIED` accepts any truthy value (implementer note).
- Task 2.2 (`565494f`): the finish-step clause says what an exit 1 under REQUIRE does, but not what to do on an exit 2 (usage or git error); line 34 is about 165 characters. The review returned `cannot_verify` for SC-5 until the controller ran `audit_skill_prompts.py` (exit 0, finish skill 560 words), so the spec verdict is pass.
- Task 2.1 (`50f7897`): the section's `Verifies:` comment had a muddled exit clause. Fixed in the comment only.

### Rollback

- `git revert -m 1 <merge-sha>` of the PR into `spec-format`.

### Not auto-verified

- That a `### Deviations` entry naming SC-n justifies the change. Traceability only: the check looks for the token.
- That an SC was not weakened before its failing row was committed, or inside the command's own test content. Out of scope by design ("What we do not claim").
- That the finish step actually stops on exit 1 under `REQUIRE_SC_STABLE=1`. Traceability only: the contract test checks the wording, not agent behaviour.
- That the walk is right across merges (R3). Judgment-tier, not exercised by a test.

### Harness-Delta

- backlog (pre-existing, found by the final re-check): `scripts/ci-strict-gate.sh` lines 82–83. When `$BASE` and HEAD share no merge base, `git diff "$BASE"...HEAD` fails, its error is swallowed, `DIFF` is empty, and the gate exits 0 having inspected nothing, even under every REQUIRE flag. This is a silent pass, confirmed with an orphan-branch probe. It predates this branch.
- backlog (high impact): a `deploy-harness.sh` run in the **main checkout** at 21:02:08 on 2026-10-09 (the `.claude/.harness-profile` mtime) rewrote 173 tracked Markdown files in this worktree. It replaced `scripts/` with `.claude/scripts/` and stripped harness-only regions; `skills/README.md` lost 127 lines. This worktree lives at `<repo>/.claude/worktrees/<name>`, inside the parent's derived `.claude/` tree, and the parent's derive-time transforms (`rewrite_derived_paths`, `strip_maintenance_docs`) walk that tree recursively. The rewrite reached this spec's `### Intent` block, which is the verbatim intent-review oracle. No code, test or run-state file was touched, and every commit made before 21:02 was clean. The controller saved the diff to `.harness-state/parent-deploy-clobber-2026-10-09.patch` and restored the files with `git restore --worktree -- .`. Fix direction: the deploy transforms must skip `.claude/worktrees/`. Also, `EnterWorktree` only accepts `.claude/worktrees/`, so every harness-native worktree is exposed to this.
