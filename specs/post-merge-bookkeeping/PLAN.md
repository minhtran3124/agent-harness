---
slug: post-merge-bookkeeping
status: shipped
owner: Minh Tran
created: 2026-07-03
---

# Phase 1 — Event-sourced bookkeeping (post-merge maintenance)

## 1. Motivation

Adoption audit (docs/research/harness-review-improvements/2026-07-03-repository-harness-recheck-v2-proposal.md) proved the
trust-ledger, CHANGELOG, and VERSION all flatlined on 2026-06-14 because they require manual
append. Make them written by the **merge event** instead: a GitHub Action on PR-merge opens a
bookkeeping PR that appends the ledger row, inserts a CHANGELOG section, and bumps VERSION.

## 2. Non-goals

- Not pushing straight to `v2` (open-PR model, per user decision — no PAT/branch-protection bypass).
- Not building the entropy audit / propose loop (Phase 3/4) — this only closes the ledger-decay loop.
- Not changing the ledger's column schema — only who writes rows.
- Not executing PR code in the workflow (metadata only; base branch only).

## 3. Success Criteria

1. `scripts/bookkeeping.sh` is pure + idempotent and fully unit-tested offline.
2. A merged feature PR would produce a correct ledger row, CHANGELOG section, and VERSION bump.
3. The workflow cannot loop (bookkeeping PRs are skipped) and cannot be script-injected via PR title.
4. `bash scripts/run-tests.sh` stays green with the new test wired in.
5. feature-intake no longer mandates a manual ledger append.

## 4. Tasks

### Task 1.1 — Bookkeeping script + unit tests

```xml
<task id="1.1" wave="1">
  <files>scripts/bookkeeping.sh, tests/scripts/bookkeeping.test.sh</files>
  <action>
Create scripts/bookkeeping.sh (bash, set -euo pipefail). Args: --pr N --title T --sha SHA
--files "<newline-separated changed paths>" [--date YYYY-MM-DD] [--root DIR]. Behavior:
  1. Idempotency: if trust-metrics.md already contains "PR #N" -> print no-op, exit 0.
  2. Resolve slug from the first `specs/<slug>/SUMMARY.md` in --files; parse Lane/Confidence/
     Flags/Affects from that SUMMARY (fallback "-" each; slug fallback "pr-N").
  3. Bump: minor if any changed file matches ^(hooks/|settings\.json|skills/), else patch;
     read/parse VERSION, compute new, write VERSION.
  4. Insert a `## [new] — DATE` CHANGELOG section (with "- TITLE (PR #N)") immediately before the
     first `## [` version heading after `## [Unreleased]` (awk).
  5. Append the ledger row to trust-metrics.md:
     | DATE | slug | lane | affects | conf | flags | - | shipped (PR #N, `SHA`) | TITLE |
  Title is only ever written to files via printf/awk vars — never eval'd.
Add tests/scripts/bookkeeping.test.sh (source tests/lib.sh) with temp-repo fixtures asserting:
  ledger row appended; CHANGELOG section inserted with the new version; VERSION patch vs minor
  (skills/ change -> minor; docs-only -> patch); SUMMARY fields parsed into the row; second run
  with same --pr is a no-op (idempotent).
  </action>
  <verify>bash tests/scripts/bookkeeping.test.sh</verify>
  <done>Script exists; all assertions pass; idempotent; no eval of untrusted input.</done>
</task>
```

### Task 2.1 — Thin workflow wrapper

```xml
<task id="2.1" wave="2">
  <files>.github/workflows/post-merge-maintenance.yml</files>
  <action>
Add the workflow: on pull_request_target types [closed] branches [v2, main];
permissions contents:write pull-requests:write. Job guard:
  if github.event.pull_request.merged == true
     && !startsWith(github.event.pull_request.head.ref, 'chore/bookkeeping-').
Steps: checkout the base branch (github.event.pull_request.base.ref, fetch-depth 0);
gather PR metadata (number, title, mergeCommit, changed files) via `gh pr view` into ENV VARS
(NOT inline ${{ }} in run: — avoid script injection); run scripts/bookkeeping.sh with those env
vars; if `git status --porcelain` shows changes, create branch chore/bookkeeping-<N>, commit
(git-actions bot identity), push, and `gh pr create` against the base branch; else no-op.
GH_TOKEN from secrets.GITHUB_TOKEN. Do NOT checkout or run PR head code.
  </action>
  <verify>python3 -c "import yaml; yaml.safe_load(open('.github/workflows/post-merge-maintenance.yml')); print('yaml ok')"</verify>
  <done>Valid YAML; guards present (merged + not-bookkeeping); metadata via env; opens a PR, never pushes to a protected branch.</done>
</task>
```

### Task 2.2 — Retire the manual ledger mandate

```xml
<task id="2.2" wave="2">
  <files>skills/feature-intake/SKILL.md</files>
  <action>
In the Guardrails section, replace the "Append to the ledger" bullet (manual append at DONE) with:
CI appends the ledger row on merge via post-merge-maintenance; the orchestrator's job is to write
a correct SUMMARY (Lane/Confidence/Flags/Affects) since the workflow parses those into the row —
then verify the bookkeeping PR after merge. Keep the "Write a Lane: line" guardrail (still needed).
  </action>
  <verify>bash scripts/run-tests.sh</verify>
  <done>Guardrail no longer mandates a manual ledger append; doc-truth lint + suite green.</done>
</task>
```

## 5. Risks

- **Workflow can't be tested locally.** Mitigation: all logic in `bookkeeping.sh` with offline unit
  tests; the YAML is thin glue reviewed by reading. First real merge is the live test — the open-PR
  model means a bug produces a bad *PR to review*, not a bad push to `v2`.
- **Loop (bookkeeping PR re-triggers).** Mitigation: `head.ref` `chore/bookkeeping-*` skip guard +
  idempotency in the script (duplicate PR# = no-op).
- **Script injection via PR title** (`pull_request_target` has write token). Mitigation: metadata via
  env vars only, never inline `${{ }}` in `run:`; title written to files via printf, never eval'd;
  PR head code never checked out.
- **Version double-bump.** Mitigation: idempotency guard; bookkeeping PRs are skipped on their own merge.

## 6. Status Log

- 2026-07-03 — plan drafted + approved (Phase 1 of v0.3). Worktree feat/post-merge-bookkeeping off v2.
