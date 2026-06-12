---
slug: harness-reliability-improvements
status: shipped
owner: Minh Tran
created: 2026-06-11
---

# Harness Reliability Improvements

> **For Claude:** REQUIRED SUB-SKILL: Use subagent-driven-development (or executing-plans in a
> parallel session) to execute this plan task-by-task.

**Goal:** Execute the 6 priority items from `docs/research-harness-req-assessment.md` — complete the
`specs/` migration, answer Q3 (Affects + PROJECT.md), move proof to machine-verified, close the
knowledge loop, and enable strict mode in CI.

**Architecture:** Each improvement follows an existing precedent in the repo: markdown convention →
exit-code script (`check_plan_format.py` is the template), bash hook with behavioral tests in `tests/hooks/`,
and every hook/settings change must keep the doc-truth lint green (the CLAUDE.md hook table ↔ `settings.json`).
Edit the **source tree** (root `hooks/`, `settings.json`, `skills/`) — do NOT touch the local `.claude/`
(the deployed copy, produced by whoever runs `deploy-harness.sh`).

**Tech Stack:** Bash (hooks, template `tests/hooks/*.test.sh`), Python 3 + pytest (scripts, template
`check_plan_format.py`/`test_check_plan_format.py`), GitHub Actions (`harness-ci.yml`).

---

## 1. Motivation

The 2026-06-11 research (`docs/research-harness-req-assessment.md`) concluded: the repo answers
4 of the 6 REQ.md questions well, but (a) Q3 "which product contract is affected?" has no mechanism
to answer it, (b) proof is self-reported (the Exit column is typed by hand, not re-run), (c) the
knowledge loop is half-closed (pull-only), (d) removing `specs/` from gitignore (06-11) is only half
done — 10 slugs are uncommitted and 2+ docs still assert the opposite, (e) the two main gates fail-open
by default (a deliberate keep-warn decision — the upgrade path is CI first, local later).

## 2. Non-goals

- Do **NOT** reverse the keep-warn decision: `REQUIRE_VERIFY` / `RISK_CORROBORATION_STRICT` **stay at 0
  locally** by default. This plan only enables strict mode in CI; enabling it locally is a separate
  decision to be made after a few weeks of breakage data from the ledger.
- Do **NOT** do items 7–9 of the research doc (story-sizing gate, `harness-audit.sh`, VERSION/CHANGELOG)
  — defer them to a later plan.
- Do **NOT** touch the local `.claude/` (memory rule: only whoever runs `deploy-harness.sh`).
- Do **NOT** build a new contract registry — Q3 is solved with the `Affects:` field + filling in
  `PROJECT.md`, exactly per the research conclusion ("no need to build a new system").
- Do **NOT** add `--all` to verify-summary (the side-effect footgun the research already warned about — YAGNI).

## 3. Success Criteria

1. `git ls-files specs/ | grep -c SUMMARY.md` ≥ 10; `specs/**/PLAN.html` is ignored; no tracked doc
   still asserts "specs/ gitignored / never committed".
2. `skills/xia2/PROJECT.md` has no remaining placeholders — the PROJECT-CONFIG-GATE of `/xia2` passes
   with this repo's real data.
3. `templates/SUMMARY.template.md` has an `Affects:` field; `/feature-intake` emits it; the ledger has
   a corresponding column.
4. `scripts/verify_summary.py` re-runs the `### Verify` table and overwrites Exit with the real exit code;
   `commit-quality-gate.sh` (when `REQUIRE_VERIFY=1`) calls it instead of grepping for presence.
5. The SessionStart hook loads INDEX + critical-patterns when the store has data, and stays silent when
   empty; the CLAUDE.md hook table matches `settings.json` (doc-truth lint green).
6. CI has a strict gate running on the PR diff with `REQUIRE_VERIFY=1` + `RISK_CORROBORATION_STRICT=1`.
7. `bash scripts/run-tests.sh` is fully green — **the official gate is CI (ubuntu + macos)**;
   locally, the settings-wiring test only goes green after a human runs `deploy-harness.sh` to sync
   `.claude/` (see the escalation in task 3.1).

## 4. Tasks

### Wave 1 — Complete the specs/ migration + Q3 foundation (4 tasks in parallel, disjoint files)

#### Task 1.1 — Ignore the derived PLAN.html + commit specs/ for the first time

```xml
<task id="1.1" wave="1">
  <files>.gitignore</files>
  <action>Add to .gitignore (replacing the commented-out `#specs/` line): `specs/**/PLAN.html` and
  `specs/**/.plan-review.json` — derived artifacts rebuildable from PLAN.md via render_plan.py;
  committing them only creates noisy HTML diffs. Then `git add specs/ .gitignore` and make the first
  commit (all existing slugs — 11 slugs including this plan's slug — + STATE.md + README.md; PLAN.html
  is excluded automatically). Note: run this on the worktree's branch, not directly on main
  (branch-guard will warn).</action>
  <verify>git check-ignore -q specs/p3-hook-fixes/PLAN.html && git ls-files specs/ | grep -q "SUMMARY.md"</verify>
  <done>specs/ is tracked (SUMMARY/PLAN.md/STATE.md), PLAN.html + the review sidecar are ignored</done>
</task>
```

#### Task 1.2 — Fix the docs that still assert "specs/ gitignored"

```xml
<task id="1.2" wave="1">
  <files>CLAUDE.md, rules/plan-format.md, skills/README.md, skills/writing-plans/SKILL.md, skills/visual-planner/SKILL.md</files>
  <action>Update every claim about the old policy to the new policy: "specs/ is tracked; only PLAN.html
  and .plan-review.json (derived artifacts) are ignored". Specifically: the CLAUDE.md Gotchas line
  "specs/ is fully gitignored ... nothing is committed"; rules/plan-format.md:125 ("plans are not
  browsable across machines" — now they are browsable); skills/README.md and writing-plans/SKILL.md
  ("specs/, which is never committed"); visual-planner/SKILL.md ("Local-only output" — PLAN.html is
  still local-only, reword the sentence to make clear it is ONLY PLAN.html, not all of specs/). Do NOT
  change the sentences that specifically describe PLAN.html as untracked (keep the "untracked" phrasing)
  — those are still correct. Note that some claims sit AFTER a backtick (e.g. "`specs/` is fully gitignored")
  so the grep cannot anchor on whitespace immediately after "specs/". Confirm with the verify command
  before finishing.</action>
  <verify>! grep -rniE "fully gitignored|local-only \(gitignored\)|is never committed|not browsable across machines" CLAUDE.md rules/ skills/ templates/</verify>
  <done>No tracked file still describes specs/ as gitignored/never-committed; the PLAN.html untracked description is intact</done>
</task>
```

#### Task 1.3 — Fill in xia2/PROJECT.md for this repo

```xml
<task id="1.3" wave="1">
  <files>skills/xia2/PROJECT.md</files>
  <action>Fill in the template following the existing structure (keep the headings), with this repo's
  real data: Identity (Name: harness-skills; Stack: Bash hooks + Python 3 scripts + Markdown skills,
  GitHub Actions CI; Repo root: ../../). High-Blast-Radius Files: settings.json (hook registration),
  hooks/*.sh (auto-run every session), skills/visual-planner/render_plan.py (core skill engine),
  templates/SUMMARY.template.md (schema machine-read by risk-corroboration + ledger), scripts/run-tests.sh
  (CI contract). Shared contracts: the 4-field SUMMARY header (Lane/Confidence/Reason/Flags) — grepped by
  risk-corroboration.sh; the ledger column in docs/harness-experimental/trust-metrics.md; the hook exit-code
  contract (0 pass / 2 block); the CLAUDE.md hook table ↔ settings.json (doc-truth lint). Test command:
  bash scripts/run-tests.sh. Solutions index: docs/solutions/INDEX.md. Cross-reference: after this task,
  re-run tests/structural/ if PROJECT.md is an input to the depth-classifier (per the maintenance discipline
  of skills/README.md). PROJECT.md has ~20 placeholders of the form &lt;...&gt; scattered throughout the
  file (not just the 3 Identity lines) — fill in or delete ALL of them, including the Session-artifacts
  section (lines 85–87) and the placeholders containing "e.g."; verify scans for both forms. Two conventions
  when filling in to avoid false-positive verifies: (1) write slug references as `specs/*/SUMMARY.md`, do NOT
  use `specs/&lt;slug&gt;/`; (2) the grep-key examples of the form `module: &lt;domain&gt;` (around line ~75)
  are guidance, not placeholders — rewrite them in backtick/no-angle-bracket form rather than deleting
  them.</action>
  <verify>! grep -qiE '<[a-z][a-z _+-]*>|<[^>]*e\.g\.[^>]*>' skills/xia2/PROJECT.md</verify>
  <done>PROJECT.md has no remaining placeholders (whole file, not just Identity); /xia2 PROJECT-CONFIG-GATE passes with the real high-blast list</done>
</task>
```

#### Task 1.4 — `Affects:` field (answering Q3) into template + intake + ledger

```xml
<task id="1.4" wave="1">
  <files>templates/SUMMARY.template.md, skills/feature-intake/SKILL.md, docs/harness-experimental/trust-metrics.md</files>
  <action>(a) templates/SUMMARY.template.md: add the line `Affects: <contract/module affected, from the
  High-Blast/Shared-Contracts list in PROJECT.md, or a module name; 'none' if none>` immediately after
  the Flags line; update the comment at the top of the file from "four header fields" to "five header
  fields". (b) skills/feature-intake/SKILL.md: in Step 2, add the instruction "cross-check the expected
  diff against the High-Blast Files + Shared Contracts in PROJECT.md to name the affected contract";
  in the Step 6 emit statement, add the `Affects:` line. (c) trust-metrics.md: add an `Affects` column to
  the table header (after the Lane column), and backfill ALL existing data rows with `-` (currently 8 rows —
  recount at execution time, the ledger is being appended to continuously; one row with the wrong column
  count breaks the machine-read table). Keep the column schema as a contract — note in the ledger header
  that this column is machine-read.</action>
  <verify>grep -q "^Affects:" templates/SUMMARY.template.md && grep -q "Affects" skills/feature-intake/SKILL.md && head -20 docs/harness-experimental/trust-metrics.md | grep -q "Affects"</verify>
  <done>Q3 has a structural foothold: intake asks, SUMMARY records, the ledger is queryable by contract</done>
</task>
```

### Wave 2 — New scripts + tests (2 tasks in parallel, disjoint files; not yet wired into a gate)

#### Task 2.1 — `scripts/verify_summary.py`: re-run the Verify table, record the real exit code

```xml
<task id="2.1" wave="2">
  <files>scripts/verify_summary.py, scripts/test_verify_summary.py</files>
  <action>Write it following the check_plan_format.py template (+ tests following test_check_plan_format.py).
  TDD: write the tests first, run them to fail, then implement. Behavior: `python3 scripts/verify_summary.py <slug>`
  (1) parse the table under `### Verify` in specs/<slug>/SUMMARY.md; (2) skip placeholder rows (Command is
  `—`, `<command>`, or empty); (3) run each Command via bash from the repo root, with a 60s timeout per command;
  (4) OVERWRITE the Exit column with the real exit code + add/refresh a `Verified: <ISO-8601>` line right below
  the table; (5) exit 1 if any command fails OR if a declared exit ≠ the real exit (print the claimed/actual
  pair), exit 0 if everything matches and passes. Add a `--check` mode: compare without overwriting (for hook/CI
  use). No `--all` (side-effect footgun). The timeout must be injectable (`--timeout <seconds>`, default 60) so
  the timeout test case can use a value of ~1s instead of burning a real 60s — this task's own verify must run
  under 60s. Minimum test cases: a matching-pass table → exit 0 + Verified line; a failing command → exit 1;
  declared 0 but actually 1 → exit 1 + mismatch message; placeholder-only → exit 0 with a "no checks ran" warning;
  timeout (--timeout 1) → exit 1; --check does not modify the file (compare content before/after).</action>
  <verify>python3 -m pytest scripts/test_verify_summary.py -x -q</verify>
  <done>Proof moves from assertion to fact: the Exit column is machine-written, mismatches are caught, there is a timestamp</done>
</task>
```

#### Task 2.2 — `hooks/session-knowledge.sh`: load knowledge at SessionStart (not yet registered)

```xml
<task id="2.2" wave="2">
  <files>hooks/session-knowledge.sh, tests/hooks/session-knowledge.test.sh</files>
  <action>Write a SessionStart hook following the JSON-output template of scope-gate.sh (additionalContext)
  and the defensive style of state-breadcrumb.sh (never block, exit 0 on every branch). Behavior:
  (1) treat the store as EMPTY when: INDEX.md does not exist, OR the Entries table has only the placeholder
  row `_(empty...)_` (the bootstrap format), OR the header reads "0 entries" with no accompanying data row
  (the rebuild format from compound/SKILL.md:387) — BOTH empty formats must stay silent and exit 0;
  (2) if there are entries (note: INDEX currently ALREADY has 2 entries after the 06-11 dogfood, so the hook
  will emit from the day it is wired — the cap is the main token-control layer): emit additionalContext
  containing the INDEX table (first 30 lines max) + the contents of docs/solutions/critical-patterns.md
  (40 lines max; if longer, take only the headings); plus one source line "[session-knowledge] docs/solutions/ —
  read the full file when relevant". This hook must NOT be registered in this task — wiring is a Rule-4 action,
  split out into task 3.1. Test cases: both empty formats → empty stdout + exit 0; missing INDEX → exit 0;
  with entries → valid JSON containing the entry name; long INDEX → truncated at the right threshold;
  critical-patterns >40 lines → headings only.</action>
  <verify>bash tests/hooks/session-knowledge.test.sh</verify>
  <done>The hook exists, tests are green, it stays silent when the store is empty — ready to wire in wave 3</done>
</task>
```

### Wave 3 — Rule-4 wiring (2 tasks in parallel, disjoint files; each task records Rollback in SUMMARY)

#### Task 3.1 — Register the SessionStart hook + update the CLAUDE.md hook table

```xml
<task id="3.1" wave="3">
  <files>settings.json, CLAUDE.md</files>
  <action>Rule-4 (scope already approved by the reviewer at intake 2026-06-11 — AskUserQuestion: "Yes — put
  it in the plan"). (a) settings.json: add a "SessionStart" trigger calling hooks/session-knowledge.sh
  (matching the exact shape of the existing entries). (b) the CLAUDE.md Hooks table: add the row
  `session-knowledge.sh | SessionStart | Load INDEX + critical-patterns into context when the store has
  data; silent when empty | ✅` — the doc-truth lint will fail if the table and settings.json diverge,
  so these two files must be edited in the SAME task. Record in specs/<slug>/SUMMARY.md under Rollback:
  `git revert <this task's sha>` (removes the registration + the table row at once). The verify covers ONLY
  the root-side checks: (a) do NOT use the full suite — task 3.2 in the same wave is editing
  hooks/commit-quality-gate.sh (flaky); (b) do NOT use tests/scripts/settings-wiring.test.sh locally — that
  test compares the root settings.json against the deployed .claude/settings.json, and syncing .claude/ is
  the HUMAN's job (memory rule: do not run deploy-harness.sh yourself) → locally it will deterministically be
  red until deploy. End the task with an explicit escalation in SUMMARY: "human runs scripts/deploy-harness.sh
  to sync .claude/, then runs tests/scripts/settings-wiring.test.sh + the full suite". CI is unaffected
  (.claude/ untracked → the check skips itself).</action>
  <verify>jq -e . settings.json >/dev/null && bash scripts/lint-doc-truth.sh</verify>
  <done>The hook is wired on the root side; doc-truth lint green; a 1-command rollback + the deploy escalation are recorded in SUMMARY; the settings-wiring test goes green after the human deploys (CI is the official gate)</done>
</task>
```

#### Task 3.2 — Upgrade `commit-quality-gate.sh`: REQUIRE_VERIFY=1 calls verify_summary --check

```xml
<task id="3.2" wave="3">
  <files>hooks/commit-quality-gate.sh, tests/hooks/commit-quality-gate.test.sh</files>
  <action>Rule-4 (hooks/*). In the existing `REQUIRE_VERIFY=1` branch (around lines 71–81): after the
  current presence check of `### Verify`, add a step that calls `python3 scripts/verify_summary.py
  --check <slug>` (resolve the slug with the exact SUMMARY-finding logic the hook already uses); an exit
  code ≠ 0 → block with a message spelling out the claimed/actual mismatch. Two constraints: (1) the default
  REQUIRE_VERIFY=0 stays as is — the keep-warn decision is not reversed; (2) when python3 is not on PATH →
  degrade to the old grep check with a warning (do not block on a missing interpreter — a deliberate fail-open,
  following the existing `|| true` style). Update the tests: case REQUIRE_VERIFY=1 + a matching Verify table →
  pass; REQUIRE_VERIFY=1 + a wrongly-declared Exit → block; REQUIRE_VERIFY=0 → behavior unchanged (regression);
  python3 absent (empty PATH simulation) → warn but do not block. Record Rollback in SUMMARY.</action>
  <verify>bash tests/hooks/commit-quality-gate.test.sh</verify>
  <done>When opt-in REQUIRE_VERIFY=1, proof is machine-re-run instead of taken on trust; the default is unchanged</done>
</task>
```

### Wave 4 — Strict mode in CI

#### Task 4.1 — CI strict gate on the PR diff

```xml
<task id="4.1" wave="4">
  <files>scripts/ci-strict-gate.sh, tests/scripts/ci-strict-gate.test.sh, .github/workflows/harness-ci.yml</files>
  <action>(a) scripts/ci-strict-gate.sh: take a base ref (default origin/main), get
  `git diff --name-only <base>...HEAD`; if the diff touches hard-gate paths — REUSE the exact
  fixed-precision pattern from risk-corroboration.sh:71
  (`(^|/)settings\.json$|^hooks/|(^|/)\.claude/hooks/|render_plan\.py$`, which already excludes
  tests/hooks/ per the false-positive lesson in the ledger), EXTENDED with `^templates/` (a deliberate
  extension not present in the original hook — note it in a comment) — then require: a changed
  specs/*/SUMMARY.md exists in the diff with `Lane: high-risk` AND ≥1 non-placeholder Verify line;
  and also run `python3 scripts/verify_summary.py --check <slug>` for the slugs whose SUMMARY changed.
  The script implements these checks itself (no shell-out to the hook — the hook reads the staged diff,
  which CI does not have); the strict semantics live in the script, not in an env var. A violation → exit 1 +
  print each missing item. A diff that does not touch a hard-gate → exit 0 silently. (b) Tests: a temporary
  fixture repo with the cases — a clean diff → 0; a diff touching hooks/ without a SUMMARY → 1; a SUMMARY with
  a low lane → 1; complete → 0; a diff touching only tests/hooks/ → 0 (the false-positive case). (c) harness-ci.yml:
  add a separate "strict-gate" JOB (not a step in the existing job — it needs its own checkout with
  fetch-depth: 0 to diff against the base) with `if: github.event_name == 'pull_request'`, running
  scripts/ci-strict-gate.sh with base = origin/${{ github.base_ref }}. This is the "enable strict in CI first"
  layer — the local default stays unchanged; read the breakage data from CI history + the ledger before
  considering enabling it locally.</action>
  <verify>bash tests/scripts/ci-strict-gate.test.sh</verify>
  <done>A PR touching a hard-gate path that lacks a high-risk SUMMARY + a real Verify will be red in CI; local is unchanged</done>
</task>
```

## 5. Risks

| Risk | Mitigation |
|---|---|
| Editing `settings.json`/`hooks/*` is high-blast (self-applied to this very repo) | Each Rule-4 task (3.1, 3.2) records a 1-command Rollback in SUMMARY before done; CI runs the same suite on ubuntu+macos |
| `verify_summary.py` runs commands with side effects | Only runs the specified slug, no `--all`; the comment in the template requires Verify commands to be idempotent/read-only |
| The SessionStart hook costs background tokens every session | The store ALREADY has 2 entries (06-11 dogfood) → the hook emits from the day it is wired; the main control layer is the 30+40 line cap + the silent branch for both empty formats |
| CI strict gate false-positive (precedent: the regex wrongly matched `tests/hooks/`) | Reuse the fixed-precision pattern from `risk-corroboration.sh`; a dedicated test case for `tests/hooks/` |
| Doc-truth lint red if the hook table and settings.json are edited in different waves | 3.1 bundles both files in one task — they can never diverge across commits |
| The first commit of specs/ drags in old sensitive content across the 10 slugs | Before `git add specs/`, do a quick secrets scan using the exact pattern of commit-quality-gate (the hook will also run automatically on commit) |

## 6. Status Log

- 2026-06-11 — Plan created (intake: Lane high-risk, Confidence medium → scope narrowed by human:
  top 1–6 + SessionStart hook; defer story-sizing/harness-audit/VERSION).
- 2026-06-11 — All 9 tasks executed (waves 1–4) via `/executing-plans` on `feat/improve-harness`.
  Commits `62b736e`..`524e27d`. Full suite green (CI gate); local `settings-wiring` red is the
  documented `.claude/` deploy-sync gap. Gate semantics refined (human-approved): ≥1 passing
  high-risk SUMMARY required, others warn.
- 2026-06-11 — shipped via `feat/improve-harness` (PR #14).
