# gh-129-durable-run-state-phase-d — Summary

Lane: normal
Confidence: high
Reason: Zero risk flags fire (no auth/authz/data-loss/audit/external-system/public-contract/
cross-platform-product-split/existing-behavior-change/weak-proof/multi-domain — this phase
documents and validates already-shipped, already-tested behavior; it does not change it). No
hard gate: no edits to `skills/*/SKILL.md`, `hooks/*`, `.claude/settings.json`, or a core skill
engine. Lane is `normal` rather than `tiny` only because the work spans >1 file and >3 discrete
steps (per `rules/plan-format.md`'s PLAN.md trigger), not because of risk.
Flags: none
Affects: specs/durable-run-state/ (new canonical spec folder), specs/STATE.md (RUN/event
ownership + compatibility boundary documentation), specs/gh-129-durable-run-state-phase-a/b/c
(SUMMARY Verify-row evidence), .github/workflows/harness-ci.yml (already runs a macOS+Ubuntu
matrix — Phase D validates against it, does not need to author a new one)
Input-type: spec slice

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<paste the original request, verbatim>
"yes, let do it"

Context established earlier in the same conversation: the user is working through GitHub issue
#129 ("Durable Run State Contract") phase by phase. Phase A (engine + CLI, PR #164), Phase B
(portable deployment, PR #166), and Phase C (core workflow checkpoints, PR #167, open against the
epic branch) are complete. This request starts Phase D.

Phase D scope, quoted verbatim from GitHub issue #129 ("Phase D — Evidence and rollout"):

- Document RUN/event ownership and the compatibility boundary with `specs/STATE.md`.
- Add a focused `research-brief.md`, `design.md`, and canonical `PLAN.md` under
  `specs/durable-run-state/`.
- Populate SUMMARY Verify rows with re-runnable evidence.
- Validate on macOS and Ubuntu through the existing CI-equivalent suite.

Acceptance criteria, quoted verbatim from the issue:

- A new run can be initialized from a spec SUMMARY and produces valid `RUN.json` + `events.jsonl`.
- Valid transitions update both artifacts consistently.
- Invalid, skipped, reversed, and post-terminal transitions fail without mutation.
- Rebuilding from `events.jsonl` reproduces the current projection.
- Duplicate event replay is idempotent; conflicting event reuse is rejected.
- Concurrent writers produce contiguous event sequences.
- Corrupt or truncated logs fail visibly and do not silently fabricate state.
- Active runs are discoverable from SessionStart/status surfaces.
- Fresh install and resync deploy `.claude/runtime/` and preserve consumer-owned additions.
- Legacy specs remain usable.
- Full harness tests pass on macOS and Ubuntu.

Non-goals, quoted verbatim from the issue: Proposal 2 retry budgets/self-healing/agentic
recovery; Slack/GitHub/Linear/PagerDuty event adapters; automatic merge detection; raw transcript
sync; multi-run archival per slug; SQLite or third-party runtime dependencies; a dashboard or
automatic policy self-modification.

Base branch: `feat/gh-129-durable-run-state` (the epic/integration branch for the whole issue,
not `main`/`loop` directly).

## What changed

Task 3.1 (regression sweep, read-only): re-ran every command listed in Phase A's and Phase B's
`SUMMARY.md` `### Verify` tables (Phase A's commands adjusted from their stale
`scripts/test_run_state.py` path to the current `runtime/test_run_state.py` path, per Phase B's
relocation), plus `python3 scripts/check_manifest.py` and the full `bash scripts/run-tests.sh`.
Every command exited 0 — no regression found, no code changed.

### Rationale

This task exists to confirm the cumulative evidence from Phase A (engine, PR #164) and Phase B
(portable deployment, PR #166) still holds after Phase D's documentation work landed in wave 1–2
of this same phase, before the epic branch's final merge decision. A clean re-run is itself the
deliverable.

### Alternatives considered

- none — this is a fixed verification sweep, not a design decision.

### Deviations

- none — every re-run command passed on the first try; no regression found, no code touched.

### Correctness Review

6-angle FIND (parallel) over `2d7d39f..6b1cb65` (docs-only diff — no code changed, so "bugs"
translate to factual errors/internal contradictions in the new documentation). Findings pooled
and fixed directly (high multi-angle corroboration substituted for a separate SCORE pass — several
findings were independently confirmed by 2-4 angles each via direct command execution):

- **Fixed (Rule 1, 4x-corroborated):** `durable-run-state/PLAN.md`'s AC-2 (now SC-2) cited the
  same test as AC-5/SC-5 (`test_idempotent_replay_and_conflict`), proving the wrong behavior.
  Changed to `test_transition_happy_path`. Commit `3871be7`.
- **Fixed (Rule 1):** AC-8/SC-8's cited test (`tests/hooks/session-knowledge.test.sh`) doesn't
  test active-run discovery in this checkout (Phase C unmerged, 0 `run_state` references).
  Changed to `test_list_active_excludes_terminal_states` (the provable engine-level capability
  today), with a note on the Phase C integration surface. Commit `3871be7`.
- **Fixed (Rule 1):** AC-10/SC-10's guard used a loose `'true' not in l` substring match (false
  negative/positive risk). Tightened to `'|| true' not in l`. Commit `3871be7`.
- **Fixed (Rule 1, schema compliance):** `durable-run-state/PLAN.md` used `AC-<n>` ids in its §3
  table, but `plan-format.md`/`verify_summary.py` only recognize `SC-<n>` — a sibling SUMMARY.md
  added later would have silently seen zero declared criteria. Renamed `AC-1..AC-11` →
  `SC-1..SC-11` throughout. Commit `3871be7`.
- **Fixed (Rule 1, 2x-corroborated):** `design.md`'s "`scripts/` and `.github/workflows/` are
  never distributed" overclaimed — `install-harness.sh`'s `PAYLOAD` does ship two named
  `scripts/*.sh` files (the load-bearing conclusion, that `harness-status.sh` isn't among them,
  was still correct). Reworded to state precisely what's true. Also fixed two minor cross-
  reference imprecisions and renamed mermaid node ids so they no longer resemble (and contradict)
  the checkpoint numbers in prose. Commit `418e0ed`.
- **Fixed (Rule 1):** `research-brief.md`'s "16-state FSM" headline was correct but its inline
  enumeration only listed 14 states, omitting `fixing_ci`/`addressing_review`. Completed the
  enumeration. Commit `09892ce`.
- **Fixed (Rule 1):** `specs/STATE.md`'s new "Compatibility boundary" paragraph ended with a
  grammatically broken, factually unsupported clause ("or vice versa is not possible..."). Removed
  it — the paragraph's actual point doesn't need the reverse claim. Commit `67ed6d3`.
- **Fixed (Rule 1, blocking):** `specs/gh-129-durable-run-state-phase-d/SUMMARY.md`'s Verify table
  was missing coverage rows for SC-1 through SC-5, failing `verify_summary.py --lane` (which
  `hooks/commit-quality-gate.sh` enforces on every commit touching this spec folder). Added the
  missing rows. Commit `294d674`.
- **Fixed (Rule 1):** This plan's own Status Log said "All 4 tasks" when 5 tasks actually exist.
  Commit `294d674`.
- **Fixed (Rule 1, structural):** Declaring cross-OS CI validation as a formal `SC-9` row made
  `--lane` permanently unsatisfiable pre-PR (no "deferred SC" mechanism exists), which would have
  blocked every subsequent commit to this folder. Removed SC-9 from the table (last row, no gap);
  moved the requirement to `PLAN.md` §5 Risks prose, matching how Phase C avoided this same trap.
  Also fixed two `grep -c "AC-"` checks left stale by the SC-rename fix above. Commit `26b6eab`.

Full suite re-run after every fix batch: ALL GREEN (214 python tests + shell suites), no
regressions. `verify_summary.py --lane` and `--check` both pass cleanly as of the final commit.

### Intent Findings

Fresh blind reviewer (no `specs/gh-129-durable-run-state-phase-d/PLAN.md` access) checked the
diff `2d7d39f~1..1e725e6` against issue #129's Phase D section (all 4 bullets + 11 acceptance
criteria) and its Non-goals, verbatim. **Verdict: faithfully implements the request.** All 4
Phase D bullets satisfied; all 11 acceptance criteria mapped in `specs/durable-run-state/PLAN.md`
§3 (confirmed `grep -c "SC-"` = 11); two cited commands spot-checked and passing; the one
criterion genuinely unprovable pre-PR (cross-OS CI) is honestly disclosed, not fabricated. No
`gap`, no `drift`, no `excess`. No routing action required.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| doc | `grep -q "RUN.json" specs/STATE.md` | 0 | specs/STATE.md documents the RUN/event ownership boundary (Task 1.1) | SC-1 |
| doc | `grep -q "runtime/run_state.py" specs/durable-run-state/research-brief.md` | 0 | research-brief.md exists and cites the real engine module (Task 1.2) | SC-2 |
| doc | `grep -q "Phase D" specs/durable-run-state/design.md` | 0 | design.md exists and documents all 4 phases (Task 1.3) | SC-3 |
| doc | `grep -q "## 3. Success Criteria" specs/durable-run-state/PLAN.md` | 0 | durable-run-state/PLAN.md exists with its own acceptance-contract table (Task 2.1) | SC-4 |
| doc | `[ "$(grep -c "SC-" specs/durable-run-state/PLAN.md)" -ge 11 ]` | 0 | durable-run-state/PLAN.md maps all 11 issue acceptance criteria (Task 2.1) | SC-5 |
| unit | `python3 -m pytest runtime/test_run_state.py -k test_init_creates_queued_run -q` | 0 | Phase A SC-1, re-run at relocated path | SC-6 |
| unit | `python3 -m pytest runtime/test_run_state.py -k test_invalid_transition_rejected -q` | 0 | Phase A SC-2, re-run at relocated path | SC-6 |
| unit | `python3 -m pytest runtime/test_run_state.py -k test_terminal_state_blocks_transition -q` | 0 | Phase A SC-3, re-run at relocated path | SC-6 |
| unit | `python3 -m pytest runtime/test_run_state.py -k test_idempotent_replay_and_conflict -q` | 0 | Phase A SC-4, re-run at relocated path | SC-6 |
| unit | `python3 -m pytest runtime/test_run_state.py -k test_corrupt_log_fails_visibly -q` | 0 | Phase A SC-5, re-run at relocated path | SC-6 |
| unit | `python3 -m pytest runtime/test_run_state.py -k test_rebuild_reproduces_projection -q` | 0 | Phase A SC-6, re-run at relocated path | SC-6 |
| unit | `python3 -m pytest runtime/test_run_state.py -k test_concurrent_writers_sequence_contiguously -q` | 0 | Phase A SC-7, re-run at relocated path | SC-6 |
| unit | `python3 -m pytest runtime/test_run_state.py -k test_shipped_requires_valid_sha -q` | 0 | Phase A SC-8, re-run at relocated path | SC-6 |
| unit | `python3 -m pytest runtime/test_run_state.py -k test_waiting_and_resume_metadata_required -q` | 0 | Phase A SC-9, re-run at relocated path | SC-6 |
| unit | `python3 -m pytest runtime/test_run_state.py -q` | 0 | Phase A full suite, 29 passed, re-run at relocated path | SC-6 |
| unit | `python3 -m pytest runtime/test_run_state.py -q` | 0 | Phase B Verify SC-1, re-confirmed | SC-6 |
| unit | `bash -c "! test -e scripts/run_state.py && ! test -e scripts/test_run_state.py"` | 0 | Phase B Verify SC-2, re-confirmed old paths still gone | SC-6 |
| integration | `bash -c 'T=$(mktemp -d); bash scripts/deploy-harness.sh --target "$T" >/dev/null 2>&1; [ -f "$T/.claude/runtime/run_state.py" ]; rc=$?; rm -rf "$T"; exit $rc'` | 0 | Phase B Verify SC-3, re-confirmed | SC-7 |
| unit | `grep -q "templates runtime settings.json" scripts/install-harness.sh` | 0 | Phase B Verify SC-4, re-confirmed | SC-7 |
| unit | `grep -q "runtime/test_run_state.py" scripts/run-tests.sh` | 0 | Phase B Verify SC-5, re-confirmed | SC-7 |
| integration | `bash tests/scripts/runtime-sync.test.sh` | 0 | Phase B Verify SC-6, re-confirmed, 6/6 cases | SC-7 |
| integration | `python3 scripts/check_manifest.py` | 0 | cumulative manifest still consistent across all phases | SC-8 |

`bash scripts/run-tests.sh` was also re-run from the repo root and confirmed ALL GREEN (214
python tests + all shell suites) as the repo-wide regression check this task requires — not
listed as its own Verify row per
`docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md` (whole-suite command
risks the 60s per-row re-run cap).

Cross-OS CI validation (`gh pr checks`, both matrix legs) cannot be proven here — no PR exists
yet for this branch. It is intentionally not a formal `SC-<n>` row in PLAN.md §3 (declaring it as
one made `verify_summary.py --lane` unsatisfiable pre-PR, per correctness-review — see PLAN.md §5
Risks); it will be verified and recorded in this SUMMARY once `finishing-a-development-branch`
opens the PR and CI runs.

### Rollback

- `git revert <sha>`

### Harness-Delta

- none

Route: /using-git-worktrees → /subagent-driven-development
