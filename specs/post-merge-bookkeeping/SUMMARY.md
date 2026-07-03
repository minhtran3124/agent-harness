<!-- Header is machine-read by risk-corroboration.sh (Lane) + trust-metrics ledger. -->

# post-merge-bookkeeping — Summary

Lane: high-risk
Confidence: high
Reason: Hard gate — adds a CI workflow with write/PR permissions and changes the trust-ledger bookkeeping process (a machine-read schema/process). High-blast (CI + ledger contract).
Flags: existing-behavior, audit-security, multi-domain
Affects: .github/workflows/post-merge-maintenance.yml, scripts/bookkeeping.sh, docs/harness-experimental/trust-metrics.md (process), CHANGELOG.md, VERSION, skills/feature-intake (Guardrails)
Input-type: harness improvement

> Lane drives ceremony; Confidence drives interruption. Hard gate forces high-risk;
> design (open-PR model, script+thin-workflow) was decided with the user, so confidence is high.

### Intent

Phase 1 của harness v0.3 (docs/harness-v03-plan-overview.md, "Event-Sourced Trust"): mọi record harness mandate phải được ghi bởi EVENT máy, không phải kỷ luật tay. Adoption audit chứng minh trust-ledger/CHANGELOG/VERSION chết đúng ngày 06-14 vì phải append tay. Fix: một GitHub Action chạy khi PR merged vào v2 → đọc metadata PR → **mở một bookkeeping PR** (mô hình open-PR đã chốt với user, không push thẳng main, không cần PAT) tự append trust-metrics row + prepend CHANGELOG + bump VERSION. Bỏ mandate "Append to the ledger" tay trong feature-intake Guardrails. Học post-merge-maintenance.yml của repository-harness nhưng an toàn hơn (open-PR thay vì push-to-main).

## What changed

- **`scripts/bookkeeping.sh`** — pure, idempotent bookkeeping logic: given a merged PR's number,
  title, merge SHA, and changed-file list, it (1) appends a `trust-metrics.md` ledger row (Lane/
  Confidence/Flags/Affects parsed from the merged `specs/<slug>/SUMMARY.md`), (2) inserts a dated
  `## [x.y.z]` CHANGELOG section, (3) bumps `VERSION` (minor when the diff touches a contract path
  `hooks/`|`settings.json`|`skills/`, else patch). Idempotent: a PR already in the ledger is a no-op.
  Logic lives in a script (not inline YAML) so it is testable offline — the Action can't be.
- **`tests/scripts/bookkeeping.test.sh`** — exercises append, CHANGELOG insert, minor/patch bump,
  SUMMARY field parsing, and idempotency, all against temp fixtures.
- **`.github/workflows/post-merge-maintenance.yml`** — thin wrapper: on `pull_request_target`
  `closed`+`merged` to `v2`/`main`, skip if the head branch is `chore/bookkeeping-*` (loop guard),
  gather PR metadata, run the script, and open a `chore/bookkeeping-<N>` PR with the result. PR
  metadata is passed via env vars (never interpolated into `run:`) to avoid Actions script injection;
  PR code is never checked out or executed (only the trusted base branch).
- **`skills/feature-intake/SKILL.md`** — Guardrails "Append to the ledger" (manual) replaced with
  "CI appends the ledger row on merge (post-merge-maintenance); verify the bookkeeping PR."

### Rationale

The whole v0.3 thesis, proven by the adoption audit on this very repo: mechanized records survive,
manual-discipline records decay. Making the ledger/CHANGELOG/VERSION written by the *merge event*
removes the discipline dependency entirely. Open-PR (not push-to-main) keeps it working without a
PAT or branch-protection bypass, at the cost of one extra merge per feature — an accepted trade.

### Alternatives considered

- Push bookkeeping straight to `v2` (like repository-harness) — rejected by the user: needs a PAT /
  branch-protection bypass. Open-PR is safer and needs only the default `GITHUB_TOKEN`.
- Inline the logic in the workflow YAML — rejected: GitHub Actions can't be run locally, so the
  logic would be untestable; a script + unit tests is the trustworthy shape (matches the repo's
  "logic in scripts, tested; workflow thin" pattern).

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| harness test suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN incl. new bookkeeping test |
| bookkeeping unit test | `bash tests/scripts/bookkeeping.test.sh` | 0 | 11 passed — append, CHANGELOG insert, bump, SUMMARY parse (plain+bold), idempotency, + review-hardening (injection, no-Unreleased, notes-anchor, pipe-escape) |
| workflow guards present (CI-safe) | `bash -c 'grep -q pull_request_target .github/workflows/post-merge-maintenance.yml && grep -q "chore/bookkeeping-" .github/workflows/post-merge-maintenance.yml'` | 0 | trigger + loop-guard both present (YAML validated separately with pyyaml: trigger=pull_request_target, job=bookkeep) |

### Rollback

- Revert the PR: `git revert <merge-sha>`.
- Disable the workflow without a revert: delete `.github/workflows/post-merge-maintenance.yml`.
- Per-file: `git checkout HEAD~1 -- scripts/bookkeeping.sh .github/workflows/post-merge-maintenance.yml skills/feature-intake/SKILL.md`

### Review outcomes

- **correctness-review** (Opus) — found 6 issues; **#1–#5 fixed** in this PR:
  - #1 (HIGH, injection): `awk -v entry` expands backslash escapes → a PR title with `\n` could
    forge a CHANGELOG heading. Fixed by passing the entry via `ENVIRON` (no escape expansion) +
    collapsing real CR/LF/tab in the title. My "injection-safe" comment was wrong for `awk -v` —
    corrected.
  - #2 (MED): CHANGELOG silently dropped when `## [Unreleased]` absent → now inserts before the
    first version heading, with an END fallback (no silent drop).
  - #3 (MED, silent data loss): idempotency grep matched free-text notes (`revert PR #8…` blocked
    real PR #8) → now anchored to the `shipped (PR #N, ` outcome marker.
  - #4 (MED): a `|` in a title added ledger table columns → title pipe-escaped for the ledger.
  - #5 (LOW): SUMMARY field parse now tolerates bold `**Lane:**` and strips trailing CR.
  - **#6 (LOW, residual)**: on an Action re-run before the bookkeeping PR merges, the branch/PR
    may already exist → job fails and needs an operator; two concurrent merges compute the same
    next version. Accepted for now (single merge-event trigger makes it rare; open-PR = a visible
    failure, not a bad push). Noted in §5 Risks.
- **intent-review** (independent model) — satisfies intent on all four asks (event-sourced,
  open-PR/no-PAT, three-way record, manual mandate removed); no scope creep into deferred phases.
  One excess flagged for sign-off: the workflow also triggers on `main` (intent named only `v2`) —
  kept deliberately as future-proofing.

### Harness-Delta

- fix-direct — this wave IS the harness-delta fix: it closes the manual-ledger decay loop the
  adoption audit found. Future waves (entropy trend, propose) build on the now-event-sourced ledger.
