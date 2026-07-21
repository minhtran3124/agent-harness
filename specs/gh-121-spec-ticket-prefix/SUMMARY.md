# gh-121-spec-ticket-prefix — Summary

Lane: high-risk
Confidence: medium
Reason: Hard gate — the change edits multiple high-blast `hooks/*` scripts and core scripts that parse `specs/<slug>/` paths; flags 6/8/10 also fired (load-bearing shared contract, test-covered existing behavior, harness-wide multi-domain sweep).
Flags: public-contracts, existing-behavior, multi-domain
Affects: specs/<slug> folder convention (shared contract) · hooks/commit-quality-gate.sh · hooks/risk-corroboration.sh · hooks/blast-radius-check.sh · hooks/branch-isolation-guard.sh · hooks/render-plan-on-write.sh · scripts/check_lane_evidence.py · skills/feature-intake (slug derivation)
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> Source: https://github.com/minhtran3124/agent-harness/issues/121 — "Spec folders: add ticket-source prefix (gh-/lin-) and sync all docs, prompts, hooks, and executing-plans path" (captured verbatim at intake, 2026-07-20)

## Motivation

Spec folders are currently named `specs/<slug>/` with a free-form kebab-case slug (see `templates/structure/specs-README.md`). There is no way to trace a spec folder back to its originating ticket (GitHub issue, Linear ticket, …). We want the folder name to carry a **ticket-source prefix**.

## Proposal

### 1. Ticket-prefixed spec folder naming

Adopt a convention such as:

- `specs/gh-<issue#>-<slug>/` — driven by a GitHub issue (e.g. `specs/gh-123-spec-folder-prefix/`)
- `specs/lin-<TEAM-###>-<slug>/` — driven by a Linear ticket (e.g. `specs/lin-ENG-315-user-quota/`)
- `specs/adhoc-<slug>/` (or plain `<slug>`, to be decided) — no external ticket

Open questions to settle during design:
- Exact prefix vocabulary (`gh-` / `lin-` / others) and the fallback for ticket-less work.
- Whether existing spec folders get migrated or grandfathered (grandfathering is likely fine — gates parse `specs/<anything>/`, but this must be verified).

### 2. Update every spec/prompt/guide/rule that references the spec-folder convention

The `specs/<slug>` convention is load-bearing across the harness. Files that reference it and need review/updating (from `grep -rlE 'specs/<slug>|specs/\*|kebab-case'`):

**Templates**
- [ ] `templates/structure/specs-README.md` — the canonical naming statement ("short kebab-case", "pick one convention per repo")
- [ ] `templates/SUMMARY.template.md`
- [ ] `templates/ESCALATIONS.template.md`

**Rules**
- [ ] `rules/plan-format.md` (frontmatter `slug: <kebab-case>`)
- [ ] `rules/orchestration.md`
- [ ] `rules/auto-correct-scope.md`
- [ ] `rules/wave-parallelism.md`

**Skills (docs + prompts)**
- [ ] `skills/feature-intake/SKILL.md` — defines slug derivation ("If absent, derive a kebab-case slug") and the tiny-lane branch name `<type>/<slug>`; this is where the prefix must be introduced at intake
- [ ] `skills/writing-plans/SKILL.md`
- [ ] `skills/executing-plans/SKILL.md`
- [ ] `skills/subagent-driven-development/SKILL.md`
- [ ] `skills/brainstorming/SKILL.md` + `spec-document-reviewer-prompt.md`
- [ ] `skills/correctness-review/SKILL.md` + reviewer/scorer prompts
- [ ] `skills/intent-review/SKILL.md` + `intent-reviewer-prompt.md`
- [ ] `skills/finishing-a-development-branch/SKILL.md`
- [ ] `skills/using-git-worktrees/SKILL.md`
- [ ] `skills/visual-planner/SKILL.md`
- [ ] `skills/compound/SKILL.md` + README + subagent prompts
- [ ] `skills/README.md`

**Hooks & scripts (parse `specs/<slug>/...` paths — verify they still match prefixed names)**
- [ ] `hooks/commit-quality-gate.sh` (Check 1.5 ESCALATIONS gate + Check 1.6 lane-evidence gate key on slug extraction)
- [ ] `hooks/risk-corroboration.sh` (reads `Lane:` from the staged SUMMARY)
- [ ] `hooks/blast-radius-check.sh` (active-plan lookup)
- [ ] `hooks/branch-isolation-guard.sh` (`specs/*` exemption)
- [ ] `hooks/render-plan-on-write.sh` (fires on `specs/*/PLAN.md`)
- [ ] `scripts/check_lane_evidence.py` (takes `<slug>` arg)
- [ ] `scripts/verify_summary.py` + `scripts/test_verify_summary.py`
- [ ] `scripts/bookkeeping.sh`, `scripts/ci-strict-gate.sh`, `scripts/harness-audit.sh`, `scripts/lint-doc-truth.sh`, `scripts/run-tests.sh`
- [ ] `skills/visual-planner/render_plan.py`

### 3. Re-verify skills that invoke executing-plans

The plan-execution path is directly coupled to the spec folder path, so audit end-to-end after the rename:

- [ ] `skills/executing-plans/SKILL.md` — Step-0 gate reads `specs/<slug>/PLAN.md`
- [ ] `skills/subagent-driven-development/SKILL.md` — dispatches per-task subagents against the plan path
- [ ] `skills/feature-intake/SKILL.md` — routing writes `specs/<slug>/SUMMARY.md` before any downstream skill runs
- [ ] `skills/writing-plans/SKILL.md` → `visual-planner` handoff (PLAN.html render path)
- [ ] Subagent contract in `rules/orchestration.md` (summaries reference the slug)
- [ ] Run `bash scripts/run-tests.sh` — CI doc-truth lint fails on missing paths, so all doc updates must land together

## Acceptance criteria

- New spec folders are created with a ticket-source prefix at intake (`/feature-intake` derives it).
- Every doc/prompt/rule listed above states the same convention (doc-truth lint green).
- All hooks/scripts that parse `specs/<...>/` paths work with prefixed folder names (existing tests + `scripts/run-tests.sh` pass).
- Existing (unprefixed) spec folders continue to work — no gate regressions.

## What changed

Wave 1 (committed: 65589ab, 3aa8bab, 90751f9, 0151d43, dab9fa4) established the ONE canonical
convention statement in `templates/structure/specs-README.md` + `specs/README.md`, the intake
derivation rule in `skills/feature-intake/SKILL.md`, and glosses in `rules/plan-format.md` +
`skills/using-git-worktrees/SKILL.md`.

Wave 2 (Task 2.1, this task) independently swept every remaining doc/prompt from issue #121's
checklist. Each was grepped for `specs/<slug>` / `<slug>` / `kebab-case` and read in context.
Result: **all confirmed-opaque — zero edits needed**. Every reference uses the slug as an opaque
folder name passed through a path template (`specs/<slug>/PLAN.md`, `specs/<slug>/SUMMARY.md`,
etc.); none restates the naming shape. The only `kebab-case` mentions in scope live in the
`skills/compound/*` files, and they belong to the **`docs/solutions/<category>/<slug>`
knowledge-base namespace** (article tags + solution-slug), a different namespace that is
correctly kebab-case-only and explicitly out of scope for this task.

| File | Outcome |
|---|---|
| templates/SUMMARY.template.md | confirmed-opaque (`specs/<slug>/SUMMARY.md` path + `<slug>` title placeholder) |
| templates/ESCALATIONS.template.md | confirmed-opaque (`specs/<slug>/ESCALATIONS.md` path + `<slug>` title placeholder) |
| rules/orchestration.md | confirmed-opaque (all `specs/<slug>/...` path templates) |
| rules/auto-correct-scope.md | confirmed-opaque (path templates + `<type>/<slug>` branch, `<slug>` CLI arg) |
| rules/wave-parallelism.md | confirmed-opaque (`specs/<slug>/PLAN.md` + `<slug>` in commit template) |
| skills/README.md | confirmed-opaque (`specs/<slug>/...` outputs; `[slug]` lines are docs/solutions namespace) |
| skills/writing-plans/SKILL.md | confirmed-opaque (path templates; line 20 already points to specs/README.md for the slug convention) |
| skills/executing-plans/SKILL.md | confirmed-opaque (`specs/<slug>/PLAN.md`, `specs/<slug>/SUMMARY.md`) |
| skills/subagent-driven-development/SKILL.md | confirmed-opaque (plan/summary path templates) |
| skills/brainstorming/SKILL.md | confirmed-opaque (`specs/<slug>/design.md` path templates) |
| skills/brainstorming/spec-document-reviewer-prompt.md | confirmed-opaque (`specs/<slug>/design.md` path) |
| skills/correctness-review/SKILL.md | confirmed-opaque (`specs/<slug>/SUMMARY.md` / ESCALATIONS.md paths) |
| skills/correctness-review/correctness-reviewer-prompt.md | confirmed-opaque (path templates + `<slug>` in agent description) |
| skills/correctness-review/correctness-scorer-prompt.md | confirmed-opaque (`specs/<slug>/SUMMARY.md` paths) |
| skills/intent-review/SKILL.md | confirmed-opaque (SUMMARY/design/ESCALATIONS path templates) |
| skills/intent-review/intent-reviewer-prompt.md | confirmed-opaque (path templates + `<slug>` in agent description) |
| skills/finishing-a-development-branch/SKILL.md | confirmed-opaque (`slug=${branch#*/}` derivation + `specs/<slug>/PLAN.md` lookup, no shape claim) |
| skills/visual-planner/SKILL.md | confirmed-opaque (render/glob path templates; frontmatter `slug` field consumed opaquely) |
| skills/compound/SKILL.md | confirmed-opaque — only `specs/<slug>/SUMMARY.md` path (opaque); `[slug]`/`kebab-case` are docs/solutions namespace (out of scope) |
| skills/compound/README.md | confirmed-opaque — no `specs/<slug>` refs; all `[slug]`/`kebab-case` are docs/solutions namespace (out of scope) |
| skills/compound/subagents/context-analyzer-prompt.md | confirmed-opaque — no `specs/<slug>` refs; `kebab-case slug` is the docs/solutions output-file slug (out of scope) |
| skills/compound/subagents/decision-extractor-prompt.md | confirmed-opaque — `specs/<slug>/SUMMARY.md` + `specs/*/SUMMARY.md` used as opaque paths |
| specs/gh-121-spec-ticket-prefix/SUMMARY.md | edited — Task 2.1 outcome table + Task 3.1 finalization (Rationale, Alternatives, real Verify rows, Rollback) |
| specs/gh-121-spec-ticket-prefix/PLAN.md | edited — Task 3.1 appended wave-2 and final Status Log entries |

Wave 3 (Task 3.1, this task) ran the full integration gate (`bash scripts/run-tests.sh` → ALL
GREEN) and made this SUMMARY evidence-complete: real `### Verify` rows (each command re-run and
its exit code recorded below), `### Rationale` / `### Alternatives considered` filled from
`design.md` + `ESCALATIONS.md`, and `### Rollback` kept. No source files were touched in wave 3 —
only the two spec bookkeeping files, committed together in the one commit permitted to touch this
slug's path (prior tasks deferred it because `commit-quality-gate.sh` Check 1.6 blocks the path
until the SUMMARY carries real lane evidence).

### Rationale

Three coupled choices, all traceable to `design.md` and the two recorded escalations:

- **Ticket-source prefix at intake only.** The prefix (`gh-<issue#>-<slug>` / `lin-<TICKET-ID>-<slug>`,
  plain `<slug>` for ticket-less work) is born at `/feature-intake` and flows through every
  downstream skill as an opaque folder name. Intake is the single point where a folder name is
  minted, so it is the only place that needs new logic; branch names inherit the prefix for free
  via the existing `<type>/<slug>` rule.
- **Verify, don't modify (hooks/scripts).** Grep evidence (design §4) showed all 10 specs-path
  parsers match the folder segment generically (`specs/<anything>/`, `^specs/[^/]+/`, `cut -d/ -f2`),
  never keying on the slug's shape. So the safe, minimal change is zero hook/script code edits plus
  two new regression-test files that prove prefixed fixtures pass every gate — mechanizing the
  grandfathering claim instead of trusting it.
- **Convention-only enforcement.** With a plain-`<slug>` fallback, an unprefixed folder is
  indistinguishable from deliberate ticket-less work, so a blocking gate is logically impossible.
  Enforcement is documentation + a derivation rule, not a new gate.

This is a pure docs/tests change (no `app/` or hook/script source touched), which is why the
high-risk lane resolved to verify-only and the whole feature is `git revert`-reversible.

### Alternatives considered

Settled in brainstorming/design (E001, E002 in `ESCALATIONS.md`; declined options in `design.md`):

- **Enforcement gate for the prefix** (declined, `design.md` → Enforcement). A blocking gate is
  logically impossible with a plain-`<slug>` fallback: an unprefixed folder cannot be
  distinguished from deliberate ticket-less work. An advisory warn was offered and declined —
  convention-only enforcement was chosen instead.
- **`adhoc-<slug>` prefix for ticket-less work** (declined, E002 option B). More explicit, but
  noisier folder names; plain `<slug>` keeps today's behavior for the no-ticket case.
- **Migrate existing spec folders** (declined, E002 option A chose grandfathering). All gates
  parse `specs/<anything>/` and treat the folder name as opaque, so existing folders keep working
  untouched; this feature's own folder is the sole, already-done rename.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Hook regression (prefixed slugs) | `bash tests/hooks/spec-prefix-compat.test.sh` | 0 | gh-/lin- fixtures pass every hook |
| Script/engine regression (prefixed slugs) | `bash tests/scripts/spec-prefix-compat.test.sh` | 0 | bookkeeping, ci-strict-gate, lane-evidence resolve prefixed slugs |
| Doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | no missing paths, hook table matches settings.json |
| Lane evidence (dogfood slug) | `python3 scripts/check_lane_evidence.py gh-121-spec-ticket-prefix` | 0 | this SUMMARY resolves against the real specs root -> evidence-complete |
| Full integration suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN — doc-truth, manifest, all bash suites, 150 python tests |

### Rollback

- `git revert <sha>` (docs/skills/hooks are all tracked; no data migration involved)

### Review Findings

- none — `/correctness-review` (six angles: enclosing-function, removed-behavior,
  call-site-impact, stack-defects, guard-completeness, prior-art) run over the full diff
  (`c6da388..23868cf`) found no defect scoring ≥80. Every hook-assertion string in both new
  test files was cross-checked against the real hook/script source and empirically confirmed
  by re-running both files directly (11/11, 5/5, exit 0).

### Advisory Findings

- `guard-completeness` (score ≤25, non-blocking): `tests/scripts/spec-prefix-compat.test.sh`'s
  `check_lane_evidence.py` failing-evidence case asserts only the exit code (`assert_rc 1`),
  which in principle cannot distinguish "correctly detected missing evidence" from "crashed
  with an unrelated exception" (Python's default uncaught-exception exit code is also 1).
  Verified empirically that in this specific case the real output is the correct detection
  message, not a traceback — not a live bug, just a theoretical test-design gap worth knowing
  if the script's error handling changes later.

### Intent Findings

- **drift (behaviorally equivalent), report-only** — `/intent-review` (blind reviewer, fresh
  `general-purpose` context, no access to PLAN.md/research-brief.md; BASE=c6da388 HEAD=f36b1dd):
  the intent's acceptance criterion "Every doc/prompt/rule listed above states the same
  convention (doc-truth lint green)" is satisfied differently than its literal wording implies —
  only 5 files got content edits (the two canonical-statement files, the intake derivation rule,
  and two one-line glosses); the ~25 other checklist files were independently confirmed to
  already reference `specs/<slug>` opaquely and needed no edit (Task 2.1's sweep). The reviewer
  judged this behaviorally equivalent to "states the same convention" (nothing contradicts it,
  doc-truth lint is green, and the intent's own §2 header says files "need review/updating," not
  "edit each") and routed it report-only rather than a gap. No other gap/drift/excess found;
  both open design questions (prefix vocabulary/fallback, migrate-vs-grandfather) confirmed
  settled coherently in design.md + ESCALATIONS.md.

### Harness-Delta

- backlog — the six `reviewer`-type correctness-angle subagents (and, earlier, all five
  per-task `reviewer`-type spec-compliance reviewers) went idle after being dispatched and
  never produced final report content, even after repeated `SendMessage` nudges over an
  extended period. `general-purpose`-type subagents (the implementers) reported reliably and
  promptly throughout the same session. Recovery both times was to perform the review directly
  in the main thread instead of continuing to wait. Worth a `/compound` entry investigating
  whether `subagent_type: reviewer` has a structural issue distinct from `general-purpose`.
