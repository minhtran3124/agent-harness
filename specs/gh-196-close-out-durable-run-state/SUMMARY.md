# gh-196-close-out-durable-run-state — Summary

Lane: high-risk
Confidence: high
Reason: Touches the `durable-run-state-checkpoints` contract (`runtime/run_state.py`) and a high-blast CI workflow (`.github/workflows/post-merge-maintenance.yml`); adds semantic validation that changes read-surface failure behavior — multiple block-mode hard-gate signals.
Flags: high-blast, public-contract, existing-behavior, weak-proof, multi-domain
Affects: durable-run-state-checkpoints (runtime/run_state.py), post-merge-maintenance workflow
Input-type: change request

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

<!-- User's verbatim request + the GH issue #196 body it points to (the intent oracle). -->

User request: "start implement for gh issue https://github.com/minhtran3124/agent-harness/issues/196"

GH issue #196 — "Close out #129: validate run history and make terminalization reliable".
Bounded close-out of the durable run-state feature (shipped in PRs #164–#168, #165). Three parts:

1. **Land semantic event-chain validation (#174).** Using the existing
   `feat/gh-174-run-state-chain-validation` work as the starting point (rebase/review, replace
   only parts that miss the current contract): validate contiguous `seq` from 1; each `from_state`
   equals the prior event's `to_state`; single `slug`/`run_id` throughout; validate each transition
   and its required waiting/resume metadata. Every read surface that trusts history (`status`,
   `list`, `rebuild`, `rebuild --check`, resume decisions) must fail visibly with the storage-error
   contract instead of projecting an impossible history — with no mutation of either artifact.
   Preserve compatibility only when explicit and bounded (scan all tracked logs first). Add
   adversarial tests for seq reuse/gaps, broken `from_state`, mixed run identity, illegal
   transitions, malformed init, and no-mutation failure behavior.

2. **Make terminalization reliable, then reconcile stale runs.** Reproduce/document the failure
   where a merged PR targeting an active integration branch absent from the workflow's static
   branch filter silently skips the `shipped` transition. Make the branch policy explicit in one
   authoritative place; a merged PR carrying a tracked run must persist exactly one `shipped` event
   with the confirmed merge SHA and stage both `RUN.json` and `events.jsonl`. Missing/non-run PRs
   stay non-fatal and observable. Add a regression test exercising the trigger/base-branch policy
   (text-only branch-list assertion is insufficient). Then reconcile each stale `ready_to_merge`
   run only when its landed SHA is confirmed; do not fabricate terminal events.

3. **Refresh the contract and close the epic.** Update canonical research/design/plan so it no
   longer advertises the fixed #177 staging defect; state the remaining branch/terminalization
   policy accurately. Re-run canonical acceptance checks, record current re-runnable evidence.
   Comment on and close #129 and #174 with links + evidence.

Acceptance criteria (from issue): every tracked `events.jsonl` passes semantic validation or has an
explicit evidence-backed repair; an impossible chain stops `status`/`list`/`rebuild --check`/resume
without mutating artifacts; existing valid lifecycle/idempotency/concurrency/rebuild/exit-code
behavior stays green; a merged PR with a tracked run reaches `shipped` exactly once with the
confirmed SHA (incl. when targeting the active integration branch); shipped persists both artifacts;
stale runs terminalized from confirmed evidence or documented as intentionally unresolved; docs match
implementation; `bash scripts/run-tests.sh` passes on Ubuntu/macOS CI; #174 and #129 closed.

Non-goals: Proposal 2 retry/self-healing; new states/SQLite/dashboards/external adapters;
`list --prompt` without a consumer; formal JSON Schema artifacts; redesigning the bookkeeping
workflow when a smaller terminalization fix suffices.

## What changed

Closed out the durable run-state feature (#129). (1) Landed semantic event-chain validation
(#174): `read_events` validates by default, so `status`, `list`, `rebuild`, `rebuild --check`, and
the resume decision reject a JSON-valid but semantically impossible log instead of trusting a
fabricated projection — without mutating either artifact; escape hatches
(`rebuild --allow-invalid-chain`, close-to-cancelled/superseded) preserved. (2) Made
terminalization reliable: added the active integration branch to the post-merge trigger allowlist
(`[main, loop, simplify]`), fixed the multi-slug picker to not skip a tracked run, restored the
`ready_to_merge` producer in finishing-a-development-branch (retired to prose by the slim refactor),
and reconciled the two stale `ready_to_merge` runs to `shipped` from confirmed merge SHAs. (3)
Refreshed the canonical durable-run-state docs to the current contract.

### Rationale

Full high-risk chain because the change alters a durable-state read contract and a high-blast CI
workflow, and must not regress the shipped lifecycle. The bulk of Part 1 already exists on
`feat/gh-174` (14 commits atop an older `simplify`); the lightest credible path is to rebase/review
that work onto current `simplify` rather than re-implement, per the issue's explicit instruction.

### Alternatives considered

- Re-implement chain validation from scratch — rejected; the issue directs reuse of the existing
  `feat/gh-174` work and it already carries adversarial tests + review receipts.
- Full bookkeeping-workflow redesign for terminalization — rejected as a non-goal; prefer the
  smallest change to the existing post-merge flow.

### Deviations

- Rule 1 — Adversarial correctness review refuted the initial full-removal of the workflow
  `branches:` filter (widened write-token surface + premature shipping on feature-branch merges);
  reverted to an integration-branch allowlist after user confirmation. `.github/workflows/post-merge-maintenance.yml`. Commit `91336a3`.
- Rule 1 — cmd_list did not validate the chain, contradicting the acceptance criterion that names
  `list`; added per-run validation with exit-3. `runtime/run_state.py`. Commit `91336a3`.
- Rule 1 — the regression test lacked `finish`, so all assertions exited 0 regardless; added it.
  `tests/scripts/post-merge-runstate-staging.test.sh`. Commit `91336a3`.
- Rule 2 — restored the `ready_to_merge` producer (retired to prose by `8e04bc5`) so terminalization
  is end-to-end. `skills/finishing-a-development-branch/SKILL.md`. Commit `91336a3`.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Mutation gate: every chain guard load-bearing | `python3 -m pytest runtime/test_chain_guards_are_load_bearing.py -q` | 0 | 15 passed | SC-1 |
| Full run-state behavior (lifecycle/idempotency/concurrency/rebuild/exit codes) | `python3 -m pytest runtime/test_run_state.py -q` | 0 | 77 passed | SC-2 |
| Tracked log validates + projection matches | `python3 runtime/run_state.py rebuild --check --slug gate-verifiability-principle` | 0 | RUN.json matches events.jsonl (seq=7) | SC-3 |
| CLI read surfaces reject an impossible chain (incl. list) | `bash tests/scripts/run-state-chain-validation.test.sh` | 0 | 14 passed | SC-4 |
| Allowlist covers active integration branch + staging contract | `bash tests/scripts/post-merge-runstate-staging.test.sh` | 0 | 11 passed | SC-5 |
| Branch-filter-gap stale run terminalized | `grep -q "\"state\": \"shipped\"" specs/gate-verifiability-principle/RUN.json` | 0 | shipped, sha=c9b3b7e | SC-6 |
| Historical-gap stale run terminalized | `grep -q "\"state\": \"shipped\"" specs/new-session-plan-resume/RUN.json` | 0 | shipped, sha=2066052 | SC-7 |
| Canonical docs state current terminalization policy | `grep -q "integration-branch allowlist" specs/durable-run-state/research-brief.md` | 0 | present | SC-8 |

### Not auto-verified

- Reconciliation of stale `ready_to_merge` runs to confirmed landed SHAs — reaches provenance (SHAs
  `2066052`/`c9b3b7e` confirmed via `gh pr view` #173/#189); appended via the real CLI, chains
  re-validate.
- **AC4 requires a follow-up main-sync PR.** The workflow allowlist change is inert until synced to
  the default branch (`main`), because `pull_request_target` loads its definition from there —
  reaches traceability (comment + regression test assert the caveat). Until a small PR lands the
  updated workflow on `main` (the historical pattern, cf. #162/#176), a PR merged into `simplify`
  still fires nothing. No CI gate yet compares the branch copy against `origin/main` (follow-up,
  tracked in `docs/harness-experimental/improvement-backlog.md`).
- `list`/`status`'s SessionStart consumers (`hooks/session-knowledge.sh`, `scripts/harness-status.sh`)
  call `list --active 2>/dev/null || true`, so the new exit-3 + `error:` line are swallowed — an
  invalid-chain run is omitted from those surfaces rather than shown as INVALID. Reaches
  traceability; the CLI itself stops visibly (AC2), and omitting an unhealthy run is no worse than
  the prior fabricated-state display. Making the consumers surface it is out of scope (pre-existing
  `2>/dev/null` pattern in hook files).
- `rebuild --allow-invalid-chain` can persist a `shipped` projection with `sha: null` — reaches
  traceability (deliberate, loud-warning escape hatch that does not unblock `transition`; advisory
  from the correctness review, score 45, below the fix threshold).
- End-to-end organic terminalization (a fresh run driven queued→shipped by the live skills) — reached
  truth only for the reconciled runs and per-surface unit/CLI tests; not re-run as a single live
  pipeline in CI.

### Rollback

- `git revert <sha>` for each landed commit; the branch is isolated and unmerged until the PR.

### Harness-Delta

- none
