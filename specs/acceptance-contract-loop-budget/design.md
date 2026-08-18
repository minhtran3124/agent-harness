# Design — Acceptance Contract + Loop Budget

Slug: `acceptance-contract-loop-budget` · Lane: high-risk · Status: user-approved (via diagram
https://claude.ai/code/artifact/24015d03-800d-4f8b-bc3c-8f38428259e4, 2026-07-22)

## Problem

The loop (implement → test → review → fix) has no objective feature-level stop condition:

1. Per-task `Verify` proves individual pieces run, but `PLAN.md §3 Success Criteria` is free
   prose no downstream stage reads mechanically. "Done" at feature level rests on reviewers
   running out of findings, not on a target defined before code.
2. The correctness-review fix-loop is textually unbounded ("auto-fix → re-review → repeat
   until ✅"). The escalate-after-repeated-failure guidance exists in `rules/orchestration.md`
   but is not mechanized inside the loop, so a pathological finding can burn tokens
   indefinitely.

## Goals

- Every plan-bearing task ships with a machine-readable acceptance contract written **before
  code**, and every post-code stage (spec review, intent review, ship gate) compares against it.
- The fix-loop terminates by construction: pass, cap, or escalate — never spin.

## Non-goals

- No change to correctness-review's plan-blind FIND stage (deliberate third-oracle design).
- No LLM-as-judge acceptance checks — contract checks are re-runnable shell commands only.
- No retrofit of existing/legacy specs (grandfathered; enforcement triggers only when a
  contract exists).
- No new hooks and no new standing automation — this extends the already-wired
  `verify_summary.py` gate (consulted `docs/solutions/harness/automation-readiness.md`).

## Component 1 — Acceptance Contract (`PLAN.md §3`)

`## 3. Success Criteria` gains a required table for new markdown plans:

```markdown
| ID | Behavior (observable) | Check (re-runnable) | Expected |
| --- | --- | --- | --- |
| SC-1 | Unauth request to create-entity is rejected | `pytest tests/routes/test_entity.py::test_unauth` | exit 0 |
```

Rules (inherit the existing Verify guardrails — see
`docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md`):

- `SC-<n>` ids, sequential, unique.
- `Expected` column grammar: `exit <n>` (usually `exit 0`; non-zero allowed — `--check`
  already passes matched non-zero claims). Free-text qualifiers may follow the token
  (e.g. `exit 0 — 401 asserted`); only the leading `exit <n>` is machine-read.
- Check commands are **pipe-free** and **<60s** (same reasons: `|` is the table delimiter;
  `ci-strict-gate.sh` re-runs commands under a 60s cap). No whole-suite rows.
- Every SC is observable behavior of the change, not an implementation detail.
- Legacy XML plans and pre-existing specs: exempt. A new markdown plan without the table
  fails plan authoring (writing-plans step), not the runtime gate.

Consumers:

| Stage | Use |
| --- | --- |
| writing-plans | Authors the table before tasks are written; tasks reference the SCs they serve |
| subagent-driven-development spec review | Per-task reviewer receives the SC rows relevant to that task |
| intent-review | Contract is an additional oracle beside the verbatim request (design.md Success Criteria already flow there today — this makes them checkable) |
| Ship exit gate | All SC proven + 0 blocking findings (below) |
| correctness-review FIND | **Not a consumer** — stays plan-blind |

## Component 2 — `Criterion` column in SUMMARY `### Verify`

The Verify table gains an **optional trailing column**:

```markdown
| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| unauth rejected | `pytest tests/routes/test_entity.py::test_unauth` | 0 | 401 asserted | SC-1 |
```

Placement decision: `verify_summary._parse_verify_rows` reads cells **positionally**
(`cells[0..3]` = Check/Command/Exit/Notes). Appending Criterion as `cells[4]` keeps every
existing 4-column SUMMARY parsing unchanged — zero migration. (The approved diagram drew
Criterion first; moved to last for backward compatibility — flagged as a deviation from the
diagram, same semantics.)

Enforcement in `verify_summary.py` (single change point — `ci-strict-gate.sh` and
`commit-quality-gate.sh` both delegate to it). SC coverage is checked in **both modes**:
`--lane` (static — the commit gate; verifies the mapping exists and claimed exits match,
never executes) and `--check` (executes commands; verifies actual exits). The plan is located
as the sibling `PLAN.md` of the resolved SUMMARY.md — lane mode via `_resolve_summary_path`'s
parent directory, check mode via its existing direct `specs_root/<slug>/` path (no resolution
refactor needed):

- When the sibling `PLAN.md` exists **and** contains an SC table: every `SC-n` must map to
  ≥1 Verify row whose `Criterion` cell names it and whose claimed exit matches. Missing
  coverage → same failure mode as today's lane-evidence errors.
- Rows without a Criterion stay legal (lint/build/misc checks).
- No PLAN.md, or PLAN.md without an SC table (tiny lane, legacy specs): behavior identical
  to today — fail-open by construction, strict only where a contract was authored.

## Component 3 — Ship exit gate (subagent-driven-development)

Before handing off to `finishing-a-development-branch`, the orchestrator requires, in order:

1. `python scripts/verify_summary.py --check <slug>` passes **including SC coverage** (Component 2).
2. Review-receipt chain complete: every entry `result: pass`, `blocking_open: 0` (exists today).

This replaces the implicit "reviews found nothing more" with an explicit conjunction:
**all SC pass ∧ 0 blocking findings**. Wording lands in the SKILL.md ship checklist; no new
script.

## Component 4 — Loop Budget (correctness-review fix-loop)

Applies to the Rule 1–3 fix-loop only (Rule 4 already STOPs immediately — unchanged):

- **Cap:** max **3** fix→re-review rounds per finding. The round counter is **in-session
  orchestrator state only** — the review receipt schema stays aggregate-only (no change to
  `templates/REVIEW-RECEIPT.template.json` or `check_review_receipt.py`); the durable record
  of a capped finding is its ESCALATIONS.md block (in-flow) or the inline report (standalone),
  plus a `Deviations` note in SUMMARY.md stating rounds used. Reaching the cap → write the
  finding to `specs/<slug>/ESCALATIONS.md` (standalone use: surface to the user) and stop
  retrying.
  Rationale for 3: round 1 fixes, round 2 addresses reviewer feedback, round 3 is the last
  chance; three fresh-context failures indicate a plan/spec problem, which is exactly the
  blocker class orchestration.md already routes to escalation.
- **Progress guard:** if between two consecutive rounds the open blocking count did not
  decrease **and** the diff content did not change (compare a hash of the full
  `git diff <base>..HEAD` output between rounds — not `--stat`, which misses same-shape
  edits; in standalone use `<base>` is the base of the diff range the review was invoked
  with), escalate immediately — do not wait for the cap. This catches ping-pong (two
  findings whose fixes revert each other) and no-op fix dispatches. A new finding surfaced
  mid-loop starts its own round counter at 1.
- The residual-work gate is unchanged: every finding ends **fixed** or **durably recorded**;
  the budget only bounds how long "fixed" may be attempted.

## Error handling / edge cases

- **Mixed tables in the wild:** parser treats `cells[4]` as absent for 4-col rows. The
  default rewrite mode (`_rewrite_table`; suppressed by `--check`) already splits and rejoins
  all cells so a 5th column round-trips — covered by a regression test, no parser rewrite.
- **Hand-authored plans bypassing writing-plans:** get no authoring-time table check (prompt-
  level enforcement only, consistent with the no-new-hooks non-goal); the runtime gate still
  applies the moment an SC table exists in the plan.
- **SC named in Verify but absent from plan:** error (typo guard), same severity as missing
  coverage.
- **Duplicate SC ids in plan:** authoring error caught by verify_summary when parsing the plan.
- **Legacy XML plans:** SC parsing is markdown-table-only; XML plans behave as "no contract".

## Testing

- Unit tests beside existing verify_summary tests: SC table parsing (plan side), 5-col row
  parsing, coverage pass/fail, typo-SC error, 4-col backward compat, legacy-plan exemption.
- `bash scripts/run-tests.sh` before commit (CLAUDE.md gotcha — hooks/scripts change);
  doc-truth lint must stay green (plan-format.md examples reference real paths only).
- Skill-text changes (correctness-review cap/progress-guard, SDD exit gate, writing-plans
  authoring step) are prompt changes: verified by `/context-propagation-audit` over the diff
  (workflow-engine surface) rather than unit tests.

## Rollout

Single branch, one PR. Components 1–3 (contract chain) and Component 4 (loop budget) are
separable — the plan should sequence them as independent waves so the loop budget is not
blocked on parser work. New plans authored after merge must include the SC table; existing
specs untouched. Rollback = `git revert` of the merge (no data, no schema).
