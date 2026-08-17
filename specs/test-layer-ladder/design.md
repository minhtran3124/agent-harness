# Design — test-layer ladder in Verify guardrails + stack testing-strategy hint

Approved by the user on 2026-08-17, with one amendment: wording must follow the terminology
profile (`rules/terminology.md`, ASD-STE100-adapted) already implemented on
`plan/terminology-artifact-authoring` — §3 vagueness bans and §1 verb distinctions apply.

## Problem

The user supplied an external testing-philosophy prompt (see `SUMMARY.md ### Intent`). Analysis
against the current workflow found ~70% already mechanized (Verify <60s guardrail, full suite at
`finishing-a-development-branch`, weakening-validation gate, escalation on repeated verify
failure). Two pieces are missing:

1. No explicit ordering between verification layers — lint/type-check first, then the smallest
   test, then integration, with the full suite reserved for branch finish. The harness encodes
   both endpoints but not the ladder between them.
2. The stack-specific lines (sequential execution default; intentional E2E/race/load/stress) have
   no home — the harness core ships no stack assumptions, so they belong in `techstacks/`.

## Decision

Approach A — minimal prose insertion into three existing locations. No new rule file (rejected: a
new auto-load/deploy surface for ~10 lines), no mechanized lint (rejected: a command's test layer
is not reliably machine-decidable from a SUMMARY row; a gate there would claim a higher tier than
it verifies).

### Exact edits

1. `rules/plan-format.md` → Guardrails, new item 4:

   > 4. **Layer ladder** — run lint and type-check first, then the smallest test that touches
   > the change. Add an integration test only when the behavior spans modules. Never put the
   > full suite in a task `Verify` or an SC row — the suite runs at
   > `finishing-a-development-branch` (the release gate).

   The final sentence deliberately reinforces the existing SC "Check" definition ("never a
   whole-suite row") — the implementer must not deduplicate that existing line.

2. `skills/subagent-driven-development/implementer-prompt.md` → "Your Job" step 3, replace
   `3. Verify implementation works` (the current wording uses `works`, a §3-banned vague term)
   with:

   > 3. Verify the implementation: run lint and type-check first, then the task's `<verify>`
   >    command. Do not substitute the full suite — the suite runs at branch finish.

3. `techstacks/README.md` → starter checklist, extend the **Testing** line:

   > **Testing** — runner, structure, coverage target. Execution strategy: sequential by
   > default or parallel-safe? Which changes need an E2E, race, load, or stress run
   > (intentional, never default)?

4. `templates/structure/techstacks-README.md` → the same **Testing** line, extended with the
   identical pinned wording as (3). Added after task review 1.3 found the gap: this template is
   the source `scripts/init-structure.sh` scaffolds into consumer projects as
   `techstacks/README.md`; the prior `techstacks-location` spec proved source/instance parity
   with `diff -q templates/structure/techstacks-README.md techstacks/README.md` → exit 0, and
   edit (3) alone breaks that parity silently (no standing test enforces it). Consumers are the
   named audience of the hint, so the template must carry it too.

## Terminology conformance

- `test` (re-runnable proof) is used for the ladder rungs, not `check` (§1: check = read state).
- No §3-banned terms (`works`, `correctly`, `properly`, `as expected`) in any inserted text; the
  one pre-existing occurrence on the edited line is replaced.
- Short sentences, one instruction each.
- `rules/terminology.md` is not on the `simplify` branch yet — conformance here is by-hand
  authoring discipline, not lint-enforced; nothing in this change depends on that branch merging.

## Error behavior

Prose-only; no schema, hook, or script change. `rules/plan-format.md` is the
`artifact-schema-plan` contract surface, but the SC-table and task grammar are untouched — the
doc-truth lint and contract suites must pass unchanged.

## Tests

- `bash scripts/run-tests.sh` passes (doc-truth lint + contract suites, unchanged behavior).
- Grep-level SC rows in `PLAN.md` prove each inserted block exists (single command, pipe-free,
  <60s each).

## Non-goals

- Pasting the full external prompt into `rules/behavior.md` (redundant with mechanized gates).
- Mechanizing ladder ordering into `verify_summary.py`.
- Editing `.claude/rules/` (deploy is user-run; `rules/plan-format.md` will drift from the
  deployed copy until the user deploys after merge).
- Adopting the STE Dictionary or claiming full ASD-STE100 compliance (matching the existing
  terminology rule's own boundary).
