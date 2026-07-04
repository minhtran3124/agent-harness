---
slug: intent-review-stage
status: shipped
owner: Minh Tran
created: 2026-06-11
---

# Intent Review Stage

> **For Claude:** REQUIRED SUB-SKILL: Use subagent-driven-development (or executing-plans in a
> parallel session) to execute this plan task-by-task.

**Goal:** Add a third oracle to the review chain — `/intent-review` checks the final diff against
the **verbatim original intent** (deliberately blind to PLAN.md), to catch the case of "passed the
plan + passed the tests but not what the user asked for".

**Architecture:** A new skill following the exact shape of `correctness-review` (thin skill + prompt template +
two standalone/in-flow entry points + residual gate), wired into `subagent-driven-development` AFTER
correctness-review and BEFORE `finishing-a-development-branch`. The oracle input is guaranteed to exist
by capturing the verbatim request into the `### Intent` section of SUMMARY right at intake. The three oracles are blind
to one another: spec-review (oracle=PLAN) · correctness-review (oracle=runtime, blind to plan) ·
intent-review (oracle=intent, blind to plan).

**Tech Stack:** Markdown skills (shape of `skills/correctness-review/`), no new hook/settings,
doc-truth lint keeps README/CLAUDE.md in sync.

---

## 1. Motivation

The current review chain has two oracles: the spec reviewer asks "does it match the PLAN?", the correctness reviewer
asks "is the runtime wrong?" (blind to plan). No gate asks "would the requester recognize this as the thing
they asked for?" — if intake/design misunderstands the intent, every layer passes consistently while the result is still wrong
(Goodhart: `<verify>` is written by the plan author themselves, and only measures what the plan thinks matters). The only human
gate after implementation is the merge PR, but there is no artifact that helps the merger check
against the intent. This gap was diagnosed in the 2026-06-11 session (see the `### Intent` and `### Rationale` of
`specs/intent-review-stage/SUMMARY.md`).

## 2. Non-goals

- **DO NOT** build a phase-level UAT/Acceptance section in the PLAN template, TEST_MATRIX-from-design,
  or a PR-body intent map — these are supplementary items, deferred until this stage has actually run ≥1 time.
- **DO NOT** add new hooks/settings — this stage is a skill prompt + wiring docs, with no machine gate.
- **DO NOT** modify correctness-review — the two oracles stay separate and are not mixed.
- **DO NOT** auto-delete "excess" (code beyond the intent) — deleting functionality is Rule-4; excess is only
  reported + requires human approval.

## 3. Success Criteria

1. `/intent-review` is invokable standalone on any diff; and is a mandatory stage in
   `subagent-driven-development` (the digraph + Red Flags + prompt list all reflect it).
2. Every new intake captures the verbatim request: `templates/SUMMARY.template.md` has `### Intent`,
   and `feature-intake` Step 6 writes it.
3. Finding taxonomy `gap / excess / drift` with clear routing (fix-loop vs escalate vs report-only)
   + residual gate (every finding: fixed-with-sha or durably recorded) — documented in SKILL.md.
4. The reviewer prompt explicitly forbids reading PLAN.md/research-brief.md (blind to plan).
5. `bash scripts/lint-doc-truth.sh` is green (README/CLAUDE.md reference the new paths that now exist);
   `bash scripts/run-tests.sh` is green — the official gate is CI (settings-wiring is locally red until
   a human deploys the sync, as noted in the previous plan).
6. The PR for this plan passes `ci-strict-gate.sh` on its own (diff touches `^templates/` → SUMMARY lane
   high-risk + real Verify rows — dogfooding the very gate just built).

## 4. Tasks

### Wave 1 — New skill + capture intent (2 parallel tasks, disjoint files)

#### Task 1.1 — Skill `/intent-review`: SKILL.md + reviewer prompt

```xml
<task id="1.1" wave="1">
  <files>skills/intent-review/SKILL.md, skills/intent-review/intent-reviewer-prompt.md</files>
  <action>Write the new skill following the exact shape of skills/correctness-review/ (frontmatter name +
  description; two entry points; pipeline; residual gate; relationship section). Mandatory
  content: (1) Oracle input — read `### Intent` from specs/SLUG/SUMMARY.md (verbatim request) +
  the Success Criteria of specs/SLUG/design.md IF it exists; if both are absent → STOP, ask the human
  to provide intent (do not infer it from the plan). (2) Blind rule — the reviewer MUST NOT read PLAN.md
  / research-brief.md; the reason is stated explicitly: symmetric with correctness-review being blind to plan to catch bugs,
  intent-review is blind to plan to catch drift. (3) Dispatch — one fresh-context reviewer subagent
  (intent-reviewer-prompt.md), receiving: the intent oracle + the full diff (BASE=before task 1,
  HEAD=current, or a range the user states when standalone) + the list of touched files. Model:
  different from the implementer (ensemble diversity, following the correctness-review convention). (4) Taxonomy + routing —
  `gap` (intent requested it, not yet shipped): clear + in scope → implementer fix-loop → re-review;
  ambiguous → ESCALATIONS.md. `drift` (shipped differently from how intent described it): equivalent behavior → record
  as advisory with an explanation; different behavior → fix-loop or escalate like a gap. `excess` (shipped
  something nobody asked for): report-only, removal needs human approval (Rule-4: removing functionality).
  (5) Residual gate — before reporting done: every finding fixed-with-sha or durably recorded (SUMMARY
  `### Intent Findings` / ESCALATIONS.md); missing is a hard block. (6) Relationship — a table comparing against
  spec-review/correctness-review/code-review (3 oracles blind to one another). Prompt template: structured
  after correctness-reviewer-prompt.md — role, input block, blind rules, output format (verdict
  table: finding | type | evidence in diff | the violated intent quote | proposed
  route), requiring a VERBATIM quote of the intent sentence for each finding (to prevent the reviewer from fabricating intent).
  INTENTIONAL difference from the correctness-review shape: there is NO SCORE/THRESHOLD stage and
  NO scorer prompt is created — routing follows the gap/excess/drift taxonomy instead of scoring; do not
  mechanically clone score/threshold from the shape.</action>
  <verify>test -f skills/intent-review/SKILL.md && test -f skills/intent-review/intent-reviewer-prompt.md && grep -q "gap" skills/intent-review/SKILL.md && grep -qi "PLAN.md" skills/intent-review/intent-reviewer-prompt.md</verify>
  <done>Skill has all 6 components, the prompt has a blind rule + output format; not yet wired anywhere (wave 2)</done>
</task>
```

#### Task 1.2 — Capture verbatim intent at intake

```xml
<task id="1.2" wave="1">
  <files>templates/SUMMARY.template.md, skills/feature-intake/SKILL.md</files>
  <action>(a) templates/SUMMARY.template.md: add a `### Intent` section right after the header block
  (before `## What changed`), with a guidance comment: "the user's VERBATIM request at intake —
  DO NOT paraphrase, do not summarize; this is the oracle for /intent-review; if the request spans multiple
  conversation turns, quote the scope-defining sentences in chronological order". DO NOT change the header block
  (6 lines: Lane/Confidence/Reason/Flags/Affects/Input-type) — the new section sits outside the grep range
  of risk-corroboration/ledger. Note the pre-existing drift (mention, do not fix in this task):
  the comment at the top of the template still says "five header fields" even though there are now 6 — report this in the summary. (b) skills/feature-intake/SKILL.md: Step 6 adds an instruction to write
  `### Intent` with the verbatim request into SUMMARY (one line in the emit block + one sentence explaining
  "oracle for /intent-review at the end of the workflow"). Execution note: this task's diff touches
  templates/ → ci-strict-gate will require this slug's SUMMARY to have Lane: high-risk + real
  Verify rows — already satisfied (specs/intent-review-stage/SUMMARY.md).</action>
  <verify>grep -q "### Intent" templates/SUMMARY.template.md && grep -q "Intent" skills/feature-intake/SKILL.md</verify>
  <done>Every new intake auto-generates the oracle for intent-review; the machine-read header is unchanged</done>
</task>
```

### Wave 2 — Wiring into the workflow (2 parallel tasks, disjoint files; after wave 1 because doc-truth lint checks that paths exist)

#### Task 2.1 — Wire the stage into `subagent-driven-development`

```xml
<task id="2.1" wave="2">
  <files>skills/subagent-driven-development/SKILL.md</files>
  <action>Update 4 places, keeping the document's prose style intact: (1) the opening sentence of the Overview: the final
  chain becomes "...final adversarial correctness review, THEN one intent review against the
  original request, before shipping". (2) Process digraph: after the node "Correctness reviewer finds
  bugs?" the "no" branch → new node "Run /intent-review (oracle: SUMMARY ### Intent + design.md;
  blind to PLAN)" → diamond "Intent findings?" → yes: "Implementer fixes gaps / escalate per
  routing" (loops back to re-review) → no: "Use finishing-a-development-branch". (3) A short new
  "Final Intent Review" section after "Final Adversarial Correctness Review": delegate to
  /intent-review, DO NOT re-implement the pipeline; state the range + the reason it exists (3 oracles blind to one
  another). (4) Red Flags add: "Skip the intent review, or hand off with unrouted intent
  findings" and "Run intent review with the implementer's context (must be fresh subagent,
  blind to PLAN.md)". (5) Example Workflow (lines ~285–297): update the closing narrative —
  after the correctness review add an intent review step before "Hand off to
  finishing-a-development-branch" (otherwise it contradicts the new digraph). Prompt Templates list:
  add a line pointing to skills/intent-review/. Note: this file is NOT scanned by lint-doc-truth —
  the verify grep is the only check, so use case-insensitive + count all 5 sites.</action>
  <verify>grep -ci "intent[- ]review" skills/subagent-driven-development/SKILL.md | awk '{exit ($1>=6)?0:1}'</verify>
  <done>The stage is mandatory in the flow: overview + digraph + section + red flags + example + prompt list all reflect it</done>
</task>
```

#### Task 2.2 — Update inventory + handoff map + workflow chain

```xml
<task id="2.2" wave="2">
  <files>skills/README.md, CLAUDE.md</files>
  <action>(a) skills/README.md: add a `/intent-review` row to the "Review & Shipping" table (Trigger:
  after correctness-review — checks the diff against the original intent, blind to PLAN; Standalone on any diff
  when there is an intent statement; Output: verdict gap/excess/drift → fix or escalation). Handoff map:
  change the subagent-driven-development line to `→ /correctness-review → /intent-review → /compound
  → /finishing-a-development-branch`, add the line `/intent-review ──► (standalone — same pipeline,
  requires ### Intent in SUMMARY or human-provided intent)`. Full Cycle diagram: insert a step
  after correctness-review. (b) CLAUDE.md: change the Skill Workflow chain to `... →
  correctness-review (final adversarial pass) → intent-review (result ↔ original intent, blind to plan)
  → compound → finishing-a-development-branch`. Run lint-doc-truth after editing — every referenced
  path must exist (wave 1 created them).</action>
  <verify>bash scripts/lint-doc-truth.sh && grep -q "intent-review" skills/README.md && grep -q "intent-review" CLAUDE.md</verify>
  <done>Inventory/handoff/chain consistent in all 3 places; doc-truth lint green</done>
</task>
```

### Wave 3 — Cross-verification + dogfood

#### Task 3.1 — Consistency sweep + run the stage on this plan's own diff

```xml
<task id="3.1" wave="3">
  <files>specs/intent-review-stage/SUMMARY.md, docs/harness-experimental/trust-metrics.md</files>
  <action>(a) Run the full suite (`bash scripts/run-tests.sh`) — accept the known locally-red
  settings-wiring (pre-deploy, CI is the gate); every other check must be green. (b) DOGFOOD: invoke
  /intent-review standalone on this plan's own diff (BASE=before wave 1), oracle = the `### Intent`
  of specs/intent-review-stage/SUMMARY.md — the new stage must be able to review itself (the first real
  smoke test: does the diff ship exactly the "third oracle, blind to plan, checking against intent" that the intent
  describes?). (c) Record the dogfood result + every finding in SUMMARY (pipe-free `### Verify` rows +
  `### Intent Findings` if any); gap/drift findings → fix right in this wave following the routing
  of the skill itself. (d) Append a ledger line to docs/harness-experimental/trust-metrics.md following the
  current 9-column schema (Affects = templates/SUMMARY.template.md + workflow chain). Note
  (c): the Verify rows written into SUMMARY must be RE-RUNNABLE on CI — ci-strict-gate re-runs them
  via verify_summary.py --check, not just as a record.</action>
  <verify>grep -q "dogfood" specs/intent-review-stage/SUMMARY.md && grep -q "intent-review-stage" docs/harness-experimental/trust-metrics.md && bash scripts/lint-doc-truth.sh</verify>
  <done>The stage is verified by itself on a real diff; SUMMARY has evidence + the ledger has a new line</done>
</task>
```

## 5. Risks

| Risk | Mitigation |
|---|---|
| Reviewer is "blind to plan" but the intent statement is too thin → useless verdict or fabricated intent | The prompt mandates a VERBATIM quote of the intent sentence for each finding; oracle absent → STOP and ask the human, do not infer from the plan |
| Intent-review becomes a rubber-stamp (always ✅ because "looks like it matches") | Adversarial shape like correctness-review: defaults to assuming ≥1 mismatch exists; the 3-type taxonomy forces the reviewer to look along each axis; the dogfood in task 3.1 is the first canary |
| The new stage lengthens the chain for tiny/normal tasks that have no design.md | The primary oracle is `### Intent` (always present after task 1.2) — design.md is not required; the stage is only mandatory in subagent-driven-development (normal/high-risk), the tiny lane does not go through this chain |
| `templates/` diff trips ci-strict-gate on the PR | Intentional (dogfooding the new gate): this slug's SUMMARY is already on the high-risk lane + will have real Verify rows before the PR |
| Two oracles for the same question when design.md exists (Intent vs Success Criteria diverge) | SKILL.md defines the hierarchy: the verbatim request wins; a divergence between the two oracles is a drift-type finding that must escalate (a signal that the design diverged from intent from the start) |

## 6. Status Log

- 2026-06-11 — Plan created (intake: Lane high-risk — hard gate templates/ + workflow redefine,
  Confidence high — solution explicitly specified by the user; brainstorming skipped: no
  design fork, the approach was settled in conversation).
- 2026-06-12 — Executed via /executing-plans (status → active). All 3 waves green.
  - Wave 1: `2ddbcc2` (1.1 skill), `40d9799` (1.2 capture intent).
  - Wave 2: `1f3cf20` (2.1 wire subagent-driven-development), `ca7a90a` (2.2 inventory/chain).
  - Wave 3: `a2a4349` (3.1 dogfood + evidence). Dogfood caught a real `gap` (specs/ untracked)
    → fixed by committing the plan; 2 advisory drift/excess findings recorded (oracle staleness).
  - Verify: 5 SUMMARY rows re-run clean via `verify_summary.py --check`; `ci-strict-gate.sh`
    OK (intent-review-stage verified); `run-tests.sh` green except known pre-deploy settings-wiring
    red (session-knowledge.sh not yet in local `.claude/` — CI is the gate).
