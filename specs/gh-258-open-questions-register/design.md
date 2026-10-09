# gh-258-open-questions-register — Design

Issue #258 item 3. Intake: `specs/gh-258-open-questions-register/SUMMARY.md` (high-risk, medium).
Visual summary of this design: https://claude.ai/artifact/RKKkpnhHPDmRPPA3rypZj3

## Goal

Give multi-phase specs one place for **non-blocking** unknowns, `specs/<slug>/QUESTIONS.md`, where
each question names the phase that must close it. When that phase ships with the question still
open, a traceability-tier check warns (warn-first), so unknowns are closed by the phase that owns
them instead of being carried forward silently.

## Current state

- Multi-phase work is a parent spec plus child specs, one per phase: `specs/codex-support/`
  (with `ROADMAP.md`) and `specs/codex-support-phase-1` … `-phase-5`; likewise
  `gh-129-durable-run-state-phase-a` … `-d`. Each child has its own `PLAN.md`.
- A phase "ships" when its `PLAN.md` frontmatter becomes `status: shipped`
  (`rules/plan-format.md` "PLAN.md structure"; `skills/finishing-a-development-branch/SKILL.md`
  step 3).
- Blocking questions already have a home: `templates/ESCALATIONS.template.md`, enforced
  deny-on-no-response by `hooks/commit-gate.sh` `check_escalations`. Non-blocking unknowns have
  none; they sit in `design.md` prose with no owner and no closing point.
- `scripts/ci-strict-gate.sh` exits 0 early (`exit 0  # no gated paths touched`) when the diff touches none of
  `hooks/`, `settings.json`, `templates/`, `render_plan.py` or `scripts/`. A PR that only flips a
  `PLAN.md` to `shipped` touches only `specs/`, so it never reaches the checks after that exit.
- `scripts/deploy-harness.sh` ships `templates/` to consumers and ships only the scripts listed in
  `CONSUMER_SCRIPTS=(`.
- No `QUESTIONS.md` exists in `specs/` today (searched `find specs -name QUESTIONS.md` on the
  `spec-format` checkout, 2026-10-09).

## Approaches considered

Where the check runs:

1. **Standalone script, called by the finish flow and by CI (chosen).** `scripts/check_open_questions.py`,
   run at finishing step 3 and in `ci-strict-gate.sh`. One-purpose, testable, and outside `hooks/`,
   so it adds no high-blast gate. Weakness: the finish step is prose an agent can skip, and a
   direct commit of `status: shipped` without a PR is caught by neither layer.
2. **Inside `verify_summary.py --check`.** No new wiring, but it widens the script that decides
   what every other gate accepts as evidence, and `--check` runs at times other than ship, so it
   would need its own "only when shipped" logic or warn on in-progress phases.
3. **A `hooks/commit-gate.sh` check on a staged `status: shipped`.** Strongest coverage and
   index-safe, but `hooks/` is high-blast (block-mode hard gate, CI block tier, consumer parity),
   and its only advantage, a hard block, is not wanted while the gate is warn-first.

What `closes-at` names: a spec slug, optionally with a task (`<slug>` or `<slug>#<task>`)
(chosen), versus a phase label such as `Phase 6` (needs a new frontmatter field to map labels to
child specs), versus a task id in the same spec only (cannot express a question that crosses
phases).

## Architecture

### 1. The register: `templates/QUESTIONS.template.md` → `specs/<slug>/QUESTIONS.md`

Optional. Usually written in the parent spec of a multi-phase effort. One block per question, in
the bullet style of `ESCALATIONS.template.md`:

```markdown
## OQ-3

- raised-by: design.md §D4
- closes-at: codex-support-phase-6
- decided-by: measurement
- default-until-closed: doctor reports advisory, never enforced
- status: open
- 2026-10-09: still open after phase 5; hook-trust input not yet observed.
```

| Field | Valid values |
|---|---|
| `## OQ-<n>` heading | positive integer; an ID is never reused |
| `raised-by` | non-empty: the document and section that raised it |
| `closes-at` | `<slug>` or `<slug>#<task-id>` |
| `decided-by` | `measurement` or `owner` |
| `default-until-closed` | non-empty: the value used while the question is open |
| `status` | `open` or `closed` |
| `closed-by` | non-empty one-line evidence; required when `status: closed` |

Other bullet lines in a block (dated progress notes) are allowed and ignored by the check. A
question that blocks work does not belong here; it is an `ESCALATIONS.md` entry. The template
header carries this exact sentence, which the contract test asserts:
`A question that blocks work does not belong here: write it in ESCALATIONS.md.`

### 2. The check: `scripts/check_open_questions.py --slug <X> [--root <dir>]`

- Reads every `specs/*/QUESTIONS.md` under the root. `--root` defaults to `Path.cwd()`, as the
  consumer-shipped `scripts/resolve_finish_context.py` does. It does **not** resolve from the
  script's own location: the deployed copy lives in `<consumer>/.claude/scripts/`, where
  `parent.parent` is `.claude/`, which holds no `specs/` and would make every check pass silently.
  Both callers run from the repository root.
- **Finding: open question.** A block with `status: open` whose `closes-at` equals `X`, or starts
  with `X#`. `X-other` does not match `X`.
- **Finding: malformed block.** A missing or empty required field, a `status` or `decided-by`
  outside its value set, a `closes-at` that is not `<slug>` or `<slug>#<task>`, a `closed` block
  without `closed-by`, or a duplicate `OQ-<n>` in one file. Malformed blocks are reported in every
  register, not only those that mention `X`, because a malformed register can hide an open
  question from the match.
- **Finding: unreadable register.** A `QUESTIONS.md` that cannot be read or decoded as UTF-8 is
  reported as a finding with its path; the script does not crash.
- **Exit codes.** No findings: exit 0, silent. Findings: printed to stderr, then exit 0 by default,
  exit 1 when `REQUIRE_QUESTIONS_CLOSED=1`. Usage error (no `--slug`): exit 2.
- `Verifies:` when slug X ships, no open question names X in `closes-at`, and every register block
  is well-formed. `Does not verify:` that a closed question was answered correctly, or that its
  `closed-by` evidence is true. Tier: traceability.

### 3. Wiring

- **`skills/finishing-a-development-branch/SKILL.md` step 3.** Before setting `status: shipped`, run
  `python3 scripts/check_open_questions.py --slug <slug>`, the same `scripts/` form as the skill's
  other helpers; deploy rewrites it to `.claude/scripts/` in a consumer's copy. On findings, tell the user and
  add an "Open questions closing here" list to the PR body. Under the default warn mode the flow
  continues.
- **`scripts/ci-strict-gate.sh`.** A new, independent section placed after the diff is computed
  (`DIFF=$(git diff --name-only "$BASE"...HEAD …)`) and **before** the
  `exit 0  # no gated paths touched` early exit. Control flow:
  1. A slug is *shipping* when `specs/<slug>/PLAN.md` is in the diff, its frontmatter at `HEAD`
     reads `status: shipped`, and at the merge base it did not. The merge base is
     `git merge-base "$BASE" HEAD`; the base version is read with
     `git show <merge-base>:specs/<slug>/PLAN.md`, and a file missing there counts as not shipped. A plan
     already shipped on the base and merely edited, such as a status-log append, is not shipping.
  2. Run the check for each shipping slug; the check prints its own findings.
  3. If any run exited 1 (only possible under `REQUIRE_QUESTIONS_CLOSED=1`), the gate exits 1.
  4. Otherwise the gate continues into the existing tier logic unchanged. The section never exits
     0 on its own, so a PR that touches `hooks/` and also ships a phase still has to carry
     high-risk proof.
- **`scripts/deploy-harness.sh`.** Add the script to `CONSUMER_SCRIPTS`, so a consumer's finish
  skill can run `.claude/scripts/check_open_questions.py`.
- **Writer guidance.** `skills/brainstorming/SKILL.md` gains one sentence: in a multi-phase spec,
  record non-blocking unknowns in `QUESTIONS.md` from the template. `templates/structure/specs-README.md`
  gains one row in its per-spec file table.

## Error behavior

| Situation | Output | Exit (default) | Exit (`REQUIRE_QUESTIONS_CLOSED=1`) |
|---|---|---|---|
| No register anywhere | none | 0 | 0 |
| Open question with `closes-at: X` or `X#<task>` | file, OQ id, default-until-closed | 0 | 1 |
| Closed question with `closed-by` | none | 0 | 0 |
| Open question for another slug | none | 0 | 0 |
| Malformed block | file, OQ id or line, the defect | 0 | 1 |
| Unreadable register | file, the error | 0 | 1 |
| Missing `--slug` | usage | 2 | 2 |

In the finish flow a warning is relayed, not acted on: the human decides whether to close the
question first. In CI a warning is visible in the job log.

## Tests

- `scripts/test_check_open_questions.py` (pytest): one case per row of the error-behavior table,
  plus `X#3.2` matching `X`, `X-other` not matching `X`, a duplicate ID, and an undecodable file
  reporting without a traceback. Tier: truth (the script is run).
- `tests/scripts/ci-strict-gate.test.sh`, three cases. Tier: truth.
  - A branch whose only change flips a `PLAN.md` to `shipped`, while an open question closes at
    that slug, prints the warning and exits 0; under `REQUIRE_QUESTIONS_CLOSED=1` it exits 1.
  - A branch that only appends to an already-shipped `PLAN.md` does not run the check.
  - A branch that touches `hooks/` and ships a phase with no open question still fails without
    high-risk proof (the section falls through).
- `tests/scripts/consumer-subset.test.sh`: the script is in the consumer subset, and the deployed
  copy run from a consumer root's `.claude/scripts/` finds a fixture register in that root's
  `specs/`. Tier: truth.
- `tests/scripts/finishing-branch-contract.test.sh`: the finish skill names
  `python3 scripts/check_open_questions.py`. A contract check asserts the template's
  blocking-question sentence. Tier: traceability.

## Success criteria

- SC-1: the script's exit codes match the error-behavior table, proven by the pytest cases.
- SC-2: a specs-only PR that ships a phase with an open question reaches the check in CI, and a
  plan that was already shipped does not, proven by the ci-strict-gate cases.
- SC-3: the new CI section never bypasses the existing tiers, proven by the hooks-plus-ship case.
- SC-4: the deployed consumer copy checks the consumer's own `specs/`, proven by the
  consumer-subset case.
- SC-5: the finish skill and the template carry the wiring and the blocking-question sentence,
  proven by the contract checks.
- SC-6: `bash scripts/run-tests.sh` stays green.

## Non-goals

- No change to `hooks/`; no blocking by default.
- No automatic closing of questions, and no change to `ESCALATIONS.md`.
- Item 2's `DC<n>` decision-change entries stay in `design.md`; they are not moved into the
  register.
- No register for single-phase specs is required; the file stays optional everywhere.

---

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | A phase ships by its own `PLAN.md` gaining `status: shipped`, committed on the PR branch before the PR opens | provenance: Local, 2026-10-09, `skills/finishing-a-development-branch/SKILL.md` step 3 | SC-2 | CI never sees a shipping event; the finish-step call remains the only layer |
| A2 | Multi-phase efforts use one spec slug per phase, so `closes-at: <slug>` can name a phase | provenance: Local, 2026-10-09, `ls specs` (`codex-support-phase-1`…`5`, `gh-129-durable-run-state-phase-a`…`d`) | accepted risk: a convention, not enforced; a phase without its own slug cannot be targeted | questions for such a phase need `<parent-slug>#<task>` instead |
| A3 | A specs-only diff currently exits `ci-strict-gate.sh` before any later check | provenance: Local, 2026-10-09, `scripts/ci-strict-gate.sh` early `exit 0`; `.github/workflows/harness-ci.yml` runs the gate on every pull request | SC-2 | if the exit moves, the new section still runs, because it sits before it |
| A4 | Consumers receive `templates/` and the scripts named in `CONSUMER_SCRIPTS`, and deploy rewrites `scripts/<name>` to `.claude/scripts/<name>` in shipped prose | provenance: Local, 2026-10-09, `scripts/deploy-harness.sh` `CONSUMER_SCRIPTS`, the `templates` sync loop and the path-rewrite block | SC-4 | the consumer finish skill would call a missing script; the step would fail loudly |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| A phase cannot ship with an open question | Warn-first: the default only prints. Blocking needs `REQUIRE_QUESTIONS_CLOSED=1`. |
| Every shipping path is checked | A direct commit of `status: shipped` with no finish step and no PR is not seen; only a `hooks/` check would see it (approach 3, deferred). |
| A closed question was answered correctly | Traceability tier: the check reads `status` and `closed-by`, not whether the evidence is true. |
| A warning is always about the phase being shipped | Malformed blocks are reported from every register (D5), so one broken register in an unrelated spec warns on every phase that ships, and fails it under `REQUIRE_QUESTIONS_CLOSED=1`. |
| Blocking questions are covered | Blocking questions stay in `ESCALATIONS.md`, which is unchanged. |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | `closes-at` is `<slug>` or `<slug>#<task-id>` | no new frontmatter field; a phase is identified by its spec slug | settled |
| D2 | The check is a standalone script, `scripts/check_open_questions.py`, called by finishing step 3 and by `ci-strict-gate.sh` | no `hooks/` change; a direct commit outside both is not checked | settled |
| D3 | Warn by default; `REQUIRE_QUESTIONS_CLOSED=1` makes findings exit 1 | same rollout shape as `REQUIRE_NOT_AUTO_VERIFIED` | settled |
| D4 | The CI section runs before the existing early exit, fires only for a plan that becomes `shipped` in the PR, and never exits 0 on its own | specs-only shipping PRs are checked; the existing tiers are never bypassed | settled |
| D5 | Malformed and unreadable registers are findings, reported in every register | a broken register cannot pass as clean; one broken register warns on every ship until fixed | settled |
| D6 | Blocking questions stay in `ESCALATIONS.md`; the register holds only non-blocking ones | two separate mechanisms with separate defaults | settled |
| D7 | `--root` defaults to the current directory, not the script's location | the deployed consumer copy reads the consumer's `specs/` | settled |
