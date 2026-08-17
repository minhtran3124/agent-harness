# test-layer-ladder — Summary

Lane: high-risk
Confidence: high
Reason: workflow-engine hard gate — edits `rules/plan-format.md` and `skills/subagent-driven-development/implementer-prompt.md` (instruction delivery / review-gate prose); scope explicitly confirmed by the user, so confidence stays high.
Flags: workflow-engine
Affects: artifact-schema-plan (rules/plan-format.md is a contract surface — prose guardrail addition only, no schema change); templates/structure (init-structure scaffold source, added by Task 1.4)
Input-type: harness improvement
Route: brainstorming → xia2 → writing-plans → using-git-worktrees → subagent-driven-development
Escalate: no (confidence high; scope explicitly approved by the user in-conversation)

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

User pasted an external testing-philosophy prompt and asked (turn 1):

> """
> Test behavior your application actually owns.
> Start with linting and type-checking.
> Run the smallest test related to the change.
> Expand to integration tests only when needed.
> Reserve the full suite for release gates.
> Run sequentially by default.
> Use E2E, race, load, and stress tests intentionally.
> Never retry failures blindly.
> Read the evidence and fix the root cause.
> Never weaken tests just to make CI green.
>
> The goal is not to run fewer tests.  The goal is to run the right tests, at the right layer, at the right time
> """
>
> xem thử có apply dc vào workflow hiện tại ko? nếu ko dc thì có thể chắt lọc dc gì để áp dụng

Assistant analysis concluded ~70% is already mechanized in the harness and proposed distilling
only the two genuinely missing pieces, then asked: "Bạn muốn tôi chạy intake cho thay đổi nhỏ
này (thêm ladder vào plan-format + hint vào techstacks) không?"

User (turn 2, approving that exact scope):

> có

Approved scope: (1) add an explicit test-layer ladder — lint/type-check → smallest targeted
test → integration when needed → full suite only at finish — to the Verify guardrails in
`rules/plan-format.md` and to the implementer verify step in
`skills/subagent-driven-development/implementer-prompt.md`; (2) add a stack-specific
testing-strategy hint (sequential default; E2E/race/load/stress used intentionally) to
`techstacks/README.md`.

## What changed

Four prose edits, no schema or hook behavior change: (1) `rules/plan-format.md` gains Guardrail 4
— the verification layer ladder (lint/type-check → smallest test → integration when the behavior
spans modules → suite at `finishing-a-development-branch`); (2) the implementer prompt's "Your
Job" step 3 now states that ordering and drops the §3-banned phrase "Verify implementation
works"; (3) `techstacks/README.md`'s starter-checklist Testing line asks the execution-strategy
questions (sequential vs parallel-safe; intentional E2E/race/load/stress); (4) the same line is
mirrored into `templates/structure/techstacks-README.md` (the init-structure scaffold source),
restoring template/instance byte parity — added mid-flight after task review 1.3 surfaced the
parity gap.

### Rationale

The harness already encodes both endpoints of the ladder (per-task Verify <60s and never
whole-suite; full suite at `finishing-a-development-branch`) but has no explicit ordering
between lint/type-check, smallest test, and integration layers; the stack-specific lines
(sequential default, intentional E2E/race/load/stress) belong in `techstacks/` because the
harness core ships no stack assumptions.

### Alternatives considered

- Paste the full external prompt into `rules/behavior.md` — rejected: ~70% redundant with
  already-mechanized gates (Verify <60s guardrail, weakening-validation gate, escalation on
  repeated verify failure), and behavior.md deliberately stays concise.
- Put the ladder in `techstacks/` too — rejected: the ladder ordering is stack-agnostic
  process (which layer, when), so it belongs with the Verify guardrails it extends.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| Layer-ladder guardrail present | `grep -q "Layer ladder" rules/plan-format.md` | 0 | | SC-1 |
| SC "Check" definition line survives | `grep -q "never a whole-suite row" rules/plan-format.md` | 0 | intentional duplication kept | SC-2 |
| Implementer step 3 states the ladder | `grep -q "run lint and type-check first" skills/subagent-driven-development/implementer-prompt.md` | 0 | | SC-3 |
| Banned vague phrase removed | `grep -q "Verify implementation works" skills/subagent-driven-development/implementer-prompt.md` | 1 | exit 1 expected — phrase absent | SC-4 |
| Techstacks Testing line extended | `grep -q "sequential by default or parallel-safe" techstacks/README.md` | 0 | | SC-5 |
| Context-matrix delivery edges intact | `python3 scripts/render_skill_prompt.py --check-all` | 0 | | SC-6 |
| Template/instance byte parity restored | `diff -q templates/structure/techstacks-README.md techstacks/README.md` | 0 | | SC-7 |

### Not auto-verified

- The no-whole-suite constraint now lives in two lines of `rules/plan-format.md` (SC "Check"
  definition and Guardrail 4) — deliberate reinforcement; a future wording change must edit both.
  Reached traceability (both lines exist per SC-1/SC-2); no gate checks they stay consistent.
- Ladder ordering is instruction, not a gate: no check verifies an implementer actually runs
  lint before its `<verify>` command — reached traceability only (the wording exists), by design
  (a command's test layer is not machine-decidable from a SUMMARY row).
- Terminology (STE) conformance of the inserted text — reached traceability (reviewers checked
  §3 banned terms by reading); `rules/terminology.md` is not on this branch, so no lint re-ran.

### Rollback

- `git revert 0d07c9a ee9cdd8 edf202d b90da10` (prose-only commits, one file each; reverting all
  four restores the prior state — revert `ee9cdd8` and `0d07c9a` together to keep template
  parity)

### Harness-Delta

- none
