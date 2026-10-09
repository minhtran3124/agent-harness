# Spec evidence rules — design

Written 2026-10-08. Pins: agent-harness `b0d2a92` (VERSION 2.28.0), issue #258.

**Status:** approved 2026-10-08. The user approved the approach, sections and restatement, and asked to continue once the spec review loop approved; it approved on round 9.
**Scope:** items 1, 2 and 4 of [#258](https://github.com/minhtran3124/agent-harness/issues/258).
Items 3, 5, 6 and 7 are out of scope.

## 1. Goal

A spec author states three things that today's specs leave implicit:

1. what the design depends on being true, and what proves each of those assumptions;
2. which guarantees a reader may expect but will not get;
3. how a settled decision is reopened.

Load-bearing numbers also show whether each was predicted, chosen as a budget, or measured. When a
measurement replaces a prediction, the prediction stays.

The source is the review of `tamnd/rupg/spec` recorded in #258. rupg's `02-the-goal.md` §2.4.4
(hypotheses H1–H6), §2.9 ("What we do not claim"), §2.10 (no target change in the change that
reports the miss), and `00-README.md` ("Settled decisions", "Rules for this folder").

## 2. Current state

- No `design.md` template exists. `skills/brainstorming/SKILL.md` (45 lines) lists topics to
  present (architecture, components/data flow, error behavior, tests) and nothing about file shape.
- `skills/xia2/references/research-brief-template.md` is the existing template pattern. Its
  Evidence Ledger labels sources `Local` / `Upstream` / `Docs` / `Inference`, but numbers carry
  no label.
- Nothing parses `design.md` sections. Three consumers read it: `writing-plans` (required input),
  `intent-review` (its Success Criteria are the secondary oracle), and `render_plan.py` (listed as a
  source file).
- The enforcement point that already exists for a design is the mandatory reviewer loop in
  `skills/brainstorming/references/spec-review-loop.md`, which dispatches
  `spec-document-reviewer-prompt.md`. The plan side has the same shape:
  `skills/writing-plans/references/review-loop.md` → `plan-document-reviewer-prompt.md`, which
  receives the approved design path.
- `rules/terminology.md` §2, with its source `specs/ste-terminology-evidence/DECISION.md`: a word does
  not force a step. "must" gave compliance in 4 of 10 runs against a competing constraint
  (measured 2026-08-13, that DECISION.md). A mandatory step belongs in a gate.

## 3. Approaches considered

| Approach | Verdict |
|---|---|
| A. Template only (prose) | Rejected. It matches the issue's "prose only" wording, but the terminology evidence above says the sections get skipped under pressure. |
| **B. Template + reviewer checks** | **Chosen.** It adds checks to two reviewer loops that already run and are mandatory. No new script and no new gate (DC1 later adds one `CONTEXT_MATRIX` entry, D12). |
| C. Template + script lint | Rejected for this batch. It touches `scripts/`, which is the CI warn tier. Matching number labels by regex is the trap in `docs/solutions/harness/ratchet-matches-spelling-not-property.md`. The issue puts scripts in later batches. `rules/terminology.md` also says a rule with no measured effect "must not be mechanised into a gate". |

## 4. Architecture

| Unit | File | Change |
|---|---|---|
| Design template | `skills/brainstorming/references/design-template.md` (new) | The output contract for `design.md`. It holds the sections of §5.1–§5.4. §5.5 is plan-side and is not in the template. |
| Brainstorming flow | `skills/brainstorming/SKILL.md` step 5 | An explicit Read of `references/design-template.md` before writing `design.md`. Write-flows do not trigger `paths:` injection (`rules/terminology.md` "Delivery"), so the skill loads the template itself. |
| Design reviewer | `skills/brainstorming/spec-document-reviewer-prompt.md` | New check rows (§6.1), plus a `[TEMPLATE_FILE_PATH]` placeholder and an instruction to Read that file before checking. The reviewer is isolated, so the §5.1–§5.4 definitions reach it only through this Read. |
| Design review loop | `skills/brainstorming/references/spec-review-loop.md` step 1 | The dispatch passes the design path, the design text, and the absolute path of `references/design-template.md`. |
| Plan link | `skills/writing-plans/SKILL.md` step 5, as its first action, before `check_plan_contract.py` | `writing-plans` writes an `Assumption coverage` list in `## 5. Risks` (§5.5). It self-checks that each referenced `SC-n` or task exists in the plan. |
| Plan reviewer | `skills/writing-plans/plan-document-reviewer-prompt.md` | A check row: the chunk that holds `## 5. Risks` lists every `A<n>` from the design (§6.2). |
| Research brief | `skills/xia2/references/research-brief-template.md` | The number-label rule (§5.4). `skills/xia2/SKILL.md` is not changed: it already fills this template, so the rule reaches xia2 through it. |
| Compound | `skills/compound/SKILL.md` | One line: a `prediction → measured` pair is a learning source. #258 item 4's target names this. |
| Delivery registry | `scripts/render_skill_prompt.py` `CONTEXT_MATRIX` | New `spec-document-reviewer` entry: `required` `design-template.md`, `required_reads` the template (D12). |
| Contract tests | `tests/scripts/brainstorming-contract.test.sh`, `writing-plans-contract.test.sh`, `compound-contract.test.sh`, `research-depth-drift.test.sh` (unchanged, must stay green), `context-propagation-regression.test.sh` | Traceability checks (§7), each in the test file of the skill it covers. |

`templates/structure/specs-README.md` is deliberately not changed. `templates/` is in the BLOCK tier
of `scripts/ci-strict-gate.sh`, and a pointer line there is not worth that cost. The template is
discoverable from `skills/brainstorming/SKILL.md`.

Data flow:

```
brainstorming ──reads──> design-template.md ──shapes──> design.md (A<n>, D<n>, DC<n>, labels)
design.md ──> spec-document-reviewer (checks §6.1) ──loop──> approved design.md
design.md ──> writing-plans ──writes Assumption coverage in ## 5. Risks──> PLAN.md
              (self-check: every referenced SC-n / Task exists in the plan)
Risks chunk + design path ──> plan-document-reviewer (checks §6.2: every A<n> is listed)
implementation reverses a decision ──user confirms (Rule 4)──> DC<n> + new D<n> in design.md
              + pointer line in SUMMARY ### Deviations
```

## 5. Template content

The template keeps the free-form sections a design already has (goal, current state, approaches,
architecture, error behavior, tests, success criteria, non-goals). It adds the four parts below,
after Non-goals and in this order: `What must be true`, `What we do not claim`, `Decisions`,
`Decision changes`.

### 5.1 What must be true (item 1)

```
## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | <a statement the design depends on> | <tier>: <source label>, <date>, <location> | <intended SC / task / check> | <what breaks, and the fallback> |
```

- IDs are `A1, A2, …`. Before approval they are renumbered to stay sequential when a row is
  deleted. After approval an ID is never reused or renumbered, and a row is never deleted: a
  `DC<n>` that drops an assumption sets its *Proven by* to `retired by DC<n>`.
- *Evidence now* has two parts. The **tier** says how strong the evidence is, using the harness
  vocabulary from `CLAUDE.md` "Gate verifiability": `traceability`, `provenance` or `truth`, or
  `none yet` when no check has confirmed the assumption. `none yet` may still carry an
  `Inference` source that says what the belief rests on. The **source** says where it came from, using
  the research-brief Evidence Ledger labels `Local`, `Upstream`, `Docs` or `Inference`, followed by
  the date it was read and its location. Example: `provenance: Local, 2026-10-08, review-loop.md`.
- #258 item 1 named the tier set as "traceability / provenance / truth, or prediction". This design
  uses `none yet` in place of `prediction`, because `prediction` is a §5.4 number label. A number
  inside an assumption still carries its §5.4 label.
- *Proven by* is never empty. It is an intended `SC-n`, task or check, or `accepted risk: <reason>`, which mirrors §5.5.
- *Proven by* is the intended proof at design time. `writing-plans` binds it to a concrete `SC-n`
  or task.
- `- none — <reason>` is allowed when the design depends on no assumption beyond its own text.

### 5.2 What we do not claim (item 1)

```
## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
```

or `- none — <reason>`. This is different from Non-goals. Non-goals bound the scope. This section
names expected guarantees that the shipped work will not give.

### 5.3 Decisions and their change rule (item 2)

```
## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | ... | ... | settled |
| D2 | ... | ... | superseded by DC1 |

## Decision changes

- DC1 — 2026-11-02 — reopens D2 — evidence: <measurement or source> — new decision: D3
```

The pointer line above the table is copied into every design, so the rule travels inside the
artifact that planning and implementation sessions read. The full rule, stated once in the template:

- A `settled` decision is reopened only by a dated `DC<n>` entry that cites evidence showing the
  decision is wrong.
- The old row stays in the table, with its status set to `superseded by DC<n>`.
- The new decision is a new `D<n>` row, with the next free ID and status `settled`. The `DC<n>`
  entry names it (`new decision: D<n>`). Readers and reviewers treat only `settled` rows as current.
- **When a decision becomes `settled`.** A `D<n>` row is `settled` from the moment the user approves
  the design (brainstorming step 5 plus the spec review loop). Before approval, rows are drafts: the
  author edits, deletes and renumbers them directly, with no `DC<n>`. `## Decision changes`
  therefore only records changes made after approval.
- **Revision pass.** A later brainstorming run on a spec whose design was already approved (a
  revised design, as `specs/codex-support/design.md` had) is the path where the design reviewer
  sees `DC<n>` entries and `superseded` rows. In that pass the settled rows are not drafts: each
  change to one is a `DC<n>`, and the §6.1 decision-change checks apply. A `DC<n>` written during
  planning or implementation is reviewed at the next revision pass, if one happens.
- **After approval** (during planning or implementation), reversing a settled decision changes
  the approved design, so it is a Rule 4 STOP under `rules/auto-correct-scope.md`. The agent asks
  the user before writing the `DC<n>`. The design reviewer loop is not re-run. The record is the
  `DC<n>` entry plus one line in `SUMMARY.md` `### Deviations` that points to it. `### Deviations`
  normally holds Rule 1–3 auto-fixes (`rules/auto-correct-scope.md` "Reporting"); the template says
  this pointer line is a deliberate extension, so it is not read as a misfiled entry.
- If the `DC<n>` adds or changes an `A<n>` after `PLAN.md` exists, the same Rule 4 step updates
  the plan's `### Assumption coverage`. The plan reviewer is not re-run for it.
- `## Decision changes` is omitted while it has no entries.
- `## Decisions` may be `- none — <reason>` when the design settles no decision.
- `settled` and `superseded by DC<n>` are the only status values. An unsettled choice is not a
  decision yet; it stays in the design's prose until it is settled.

### 5.4 Number labels (item 4)

A number is **load-bearing** when a decision, target, threshold or Success Criterion depends on it.
Each value of a load-bearing number carries exactly one label:

- `prediction` — an estimate not yet measured;
- `budget` — a limit we chose;
- `measured <YYYY-MM-DD> <source>` — a value observed, with its date and where it came from.

When a measurement replaces a prediction, the prediction keeps its label and the measurement is
appended beside it with its own:
`80 ms (prediction) → 92 ms (measured 2026-11-02, <run>)`. Illustrative numbers stay unlabelled.

The same rule goes into the research-brief template. There it complements the Evidence Ledger's
source labels: the ledger says where a fact came from, and the number label says whether a number
was observed.

### 5.5 Assumption coverage in the plan (plan link)

`writing-plans` adds this list to `PLAN.md` `## 5. Risks` at authoring-flow step 5, after the tasks
exist and before `check_plan_contract.py` runs, so the contract check and the review loop both see
the final list. `rules/plan-format.md` leaves Risks free-form, so the plan format
does not change:

```
## 5. Risks

- **<risk title>** — <body>. Mitigation: <text>
- ...

### Assumption coverage

- A1 → SC-2
- A2 → Task 1.3
- A3 → accepted risk: <reason>
```

Rules:

- Each `A<n>` of the design appears exactly once. Before the review loop, `writing-plans` checks
  that every `SC-n` and task named in the list exists in the plan.
- **Position.** The subsection comes after the risk bullets, separated by a blank line. When the plan
  has no risks, the section still starts with `- none` before the subsection. That `- none` renders as
  one untitled risk card with the body "none", which is how an empty Risks list renders today. Reason:
  `render_risks()` in `skills/visual-planner/render_plan.py` turns only the first bullet list of the
  section into risk cards and renders the rest as prose (Local, 2026-10-08, lines 1197–1232). A
  coverage list placed first would render as risk cards.
- A design with `- none — <reason>` under `What must be true` gives `- none (design has no
  assumptions)`.
- A design without a `## What must be true` section (a legacy design, §6.3), or no `design.md` at
  all (lanes where the artifact policy does not require one), gives no subsection. The plan
  reviewer skips the §6.2 check in both cases.

## 6. Error behavior

### 6.1 Design reviewer

The reviewer reports an issue when any of these hold. The `DC<n>` and `superseded` checks only
fire in a revision pass (§5.3); on a first design they have nothing to match.

- `What must be true`, `What we do not claim` or `Decisions` is missing, or holds placeholder text
  (a `- none — <reason>` line is valid in each);
- an `A<n>` row has an empty *Proven by* or *If false*, or an *Evidence now* outside the §5.1
  vocabulary;
- `A<n>`, `D<n>` or `DC<n>` IDs are not sequential, or one is reused;
- a load-bearing number has no §5.4 label;
- a decision status is neither `settled` nor `superseded by DC<n>`;
- a `superseded` decision has no matching `DC<n>` entry;
- a `DC<n>` entry cites no evidence;
- a `DC<n>` names a `new decision: D<n>` that is not a `settled` row, or reopens a decision whose
  status is not `superseded by DC<n>`;
- `## Decisions` has a table but lacks the reopen pointer line (`To reopen a settled decision
  after approval …`). D10 depends on that line, so a design that drops it fails review.

The existing loop handles it: fix, re-review, and after 5 rounds (budget, existing rule in
`spec-review-loop.md`) stop and ask the user.

### 6.2 Plan reviewer

The plan reviewer is dispatched per chunk and is scoped to that chunk and the design path, so it
does not judge the whole plan. The check is therefore split:

- **The reviewer** checks only the chunk that holds `## 5. Risks`, and only when the design has a
  `## What must be true` section. It reports an `A<n>` from the design that is missing from
  `### Assumption coverage` or listed twice, and a coverage subsection placed before the risk
  bullets or with no blank line after them (it would fold into the last risk card). When the design's section is `- none — <reason>`, the reviewer accepts
  `- none (design has no assumptions)` as complete. The check needs only the chunk and the design.
  Other chunks skip it. When the design has `What must be true` rows but the Risks chunk has no
  `### Assumption coverage` subsection, the reviewer reports one issue that names every `A<n>`.
- **`writing-plans` itself** checks that each `SC-n` or task named in the list exists in the plan
  (§5.5). That needs the whole plan, which only the author holds.

The writing-plans loop is advisory with a stated rationale (`review-loop.md`), so an unresolved
objection needs an explicit reason in the plan.

### 6.3 Legacy specs

`design.md` files written before this change are exempt. No skill re-reads a shipped spec to
enforce the template. This matches the "spec archaeology" exclusion in `rules/terminology.md`.

## 7. Tests

Traceability-tier checks, each in the existing contract test of the skill it covers: checks 1–3
and 5 in `brainstorming-contract.test.sh` (check 5 covers xia2's template, which brainstorming's
template mirrors), check 4 in `writing-plans-contract.test.sh`, check 6 in
`compound-contract.test.sh`. Each check is a fixed-string `grep -qF` for the quoted anchor.

1. `skills/brainstorming/references/design-template.md` exists, and `skills/brainstorming/SKILL.md`
   contains `references/design-template.md`.
2. The template contains `To reopen a settled decision after approval`, `## What must be true`,
   `## What we do not claim`, `## Decisions`,
   `## Decision changes`, `` `prediction` ``, `` `budget` `` and `` `measured <YYYY-MM-DD> <source>` ``.
3. `skills/brainstorming/spec-document-reviewer-prompt.md` contains `What must be true`,
   `Proven by`, `load-bearing`, `superseded by`, `Decision changes`,
   `To reopen a settled decision` and `[TEMPLATE_FILE_PATH]`,
   and `skills/brainstorming/references/spec-review-loop.md` contains `design-template.md`. This
   anchor shows the definitions are delivered to the isolated reviewer, not only named.
4. `skills/writing-plans/SKILL.md` and `skills/writing-plans/plan-document-reviewer-prompt.md` each
   contain `Assumption coverage`, and `skills/writing-plans/SKILL.md` contains
   `after the risk bullets`.
5. `skills/xia2/references/research-brief-template.md` contains `` `measured <YYYY-MM-DD> <source>` ``.
6. `skills/compound/SKILL.md` contains `prediction → measured`.
7. `python3 scripts/render_skill_prompt.py --check-all` exits 0 with the new `CONTEXT_MATRIX`
   entry, and a new mutation case in `context-propagation-regression.test.sh` shows that deleting
   the reviewer's template Read makes `--check-all` fail (D12).

These checks show the instructions are present. They do not show that agents follow them (see
`What we do not claim`). Skill prose changes, so `context-propagation-audit` runs on the diff
and covers delivery to: the brainstorming main session, the design reviewer subagent,
`writing-plans`, the plan reviewer subagent, and the xia2 session. The audit also records that the `### Deviations` pointer line
extends `rules/auto-correct-scope.md` "Reporting" (Rule 1–3 only) without editing that rule.

## 8. Success criteria

Machine-decidable (one `SC-n` row per test file; do not split a file into per-check rows):

1. `bash tests/scripts/brainstorming-contract.test.sh`, `bash tests/scripts/writing-plans-contract.test.sh`,
   `bash tests/scripts/compound-contract.test.sh`, `bash tests/scripts/research-depth-drift.test.sh`
   and `bash tests/scripts/context-propagation-regression.test.sh` each exit 0, with the §7 checks
   included.

Cited in prose at finishing, not an `SC-n` row (`rules/plan-format.md` guardrail 4 forbids a
whole-suite command there):

2. `bash scripts/run-tests.sh` exits 0.

Behavioral (judgment-tier; recorded in `SUMMARY.md` `### Not auto-verified`):

3. A design written through brainstorming after this change has the three new sections, or a
   `- none — <reason>` in each.
4. The design reviewer, given the new prompt, reports an issue on a design that omits them. One
   dry run after implementation against a stripped copy of this design; its result and tier are
   recorded in `SUMMARY.md` `### Not auto-verified`.
5. A plan written from such a design carries an `Assumption coverage` list that names every `A<n>`.

The PR touches no BLOCK-tier path of `scripts/ci-strict-gate.sh` (`hooks/`, `settings.json`,
`templates/`, `render_plan.py`). The `workflow-engine` signal still applies, so the
`context-propagation-audit` receipt is required.

## 9. Non-goals

- Item 3 (open-questions register), item 5 (no goalpost moves in `verify_summary.py`), items 6–7.
- Any script, hook, gate or `rules/*.md` change, including `rules/plan-format.md`, except the one
  `CONTEXT_MATRIX` entry of D12.
- Rewriting existing `design.md` files to the template.
- Adopting ASD-STE100. `rules/terminology.md` already records that decision.

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | The design reviewer loop runs on every design that brainstorming writes. | traceability: Local, 2026-10-08, `spec-review-loop.md` step 1 makes the dispatch mandatory; `scripts/test_check_skill_tool_conformance.py` only checks that the skill may use Agent/Task. | accepted risk: the existing contract test and §7 check 3 show only that the loop reference and the prompt text exist (traceability), not that the dispatch runs. | The §6.1 checks never run. The sections fall back to prose only, which is approach A. |
| A2 | A reviewer subagent can tell a load-bearing number from an illustrative one using the §5.4 definition. | none yet: Inference, 2026-10-08, spec review rounds 1 and 3 of this design, where the reviewer sorted the design's own numbers into load-bearing and illustrative without the definition. | accepted risk: judgment-tier until the post-implementation dry run of Success criterion 4. | Expect false positives. The fallback is to narrow the check to numbers in `Decisions`, `What must be true` and Success Criteria. |
| A3 | The plan reviewer receives the design path and the chunk that holds `## 5. Risks`, which is enough for the §6.2 check. | traceability: Local, 2026-10-08, `writing-plans/references/review-loop.md` passes "the chunk and approved design path". | §7 check 4 (the prompt text exists) and the context-propagation audit (the design path reaches the reviewer). | The plan check cannot run. The fallback is to paste the `What must be true` table into the plan reviewer's input. |
| A4 | Adding sections to the design does not break its consumers (`writing-plans`, `intent-review`, `render_plan.py`). | provenance: Local, 2026-10-08, a grep found no parser of design sections except intent-review's Success Criteria lookup. | accepted risk: no targeted test parses design sections; the full suite (Success criterion 2) runs in prose at finishing. | A consumer that keys on headings misreads the design. The fix is in that consumer. |
| A5 | The `### Assumption coverage` subsection does not change how `PLAN.html` renders the risks, when it follows the §5.5 position rule. | provenance: Local, 2026-10-08, `render_plan.py` lines 1140–1232, `render_risks()` and `_md_list_items()`. | §7 check 4 (the position rule is in `writing-plans`), then a rendered plan from the first real use. | Coverage lines render as risk cards. `render_plan.py` is in the CI BLOCK tier, so the fix is a separate change. |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| Agents always fill the sections truthfully. | The reviewer checks presence and shape. Like `### Not auto-verified`, `- none — <reason>` satisfies it, which forces the question but not an honest answer. |
| A mechanical gate blocks a design without the sections. | Approach C was rejected for this batch (§3). Enforcement is the reviewer loop only. |
| Existing specs follow the template. | Legacy specs are exempt (§6.3). |
| Every number in a spec is labelled. | Only load-bearing numbers are (§5.4). |
| Numbers in `research-brief.md` carry labels. | No reviewer loop runs on `research-brief.md`. The label rule is advisory there, which is approach A for that file only. The labels are enforced where they are load-bearing for a decision: in `design.md`, through the design reviewer. |
| Every plan carries a complete `Assumption coverage` list. | The writing-plans review loop is advisory (§6.2): a missing or partial list can ship with a stated rationale. |
| A decision reversed during implementation is always recorded as a `DC<n>`. | The rule reaches planning and implementation only through the pointer line in the design (D10). An implementer who never opens `design.md` relies on the Rule 4 STOP and the user alone. |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | Enforce through the two existing reviewer loops, not a script. | No change under `scripts/` or `hooks/`. Enforcement is judgment-tier. | superseded by DC1 |
| D2 | The design template lives in `skills/brainstorming/references/` and is read explicitly at step 5. | The same pattern as xia2's template. `paths:` injection is not relied on. | settled |
| D3 | Assumption IDs are `A<n>`, decision IDs `D<n>`, decision-change IDs `DC<n>`. | `writing-plans` and both reviewers use these IDs. | settled |
| D4 | Until item 3 ships, decision changes live in the spec's own `## Decision changes` section. | Item 3's register replaces it later, through its own `DC` entry. | settled |
| D5 | Number labels apply to load-bearing numbers only. | Lower authoring cost. The reviewer must judge "load-bearing" (A2). | settled |
| D6 | Assumption evidence is `<tier>: <source>`, with the gate-verifiability tiers and the Evidence Ledger source labels. `none yet` replaces #258's `prediction`. | No new vocabulary. `prediction` stays a number label only (§5.1 states the departure from #258). | settled |
| D7 | The plan-side check is split: the reviewer checks the list is complete, and `writing-plans` checks the references exist. | Works with per-chunk review. `rules/plan-format.md` and `review-loop.md` stay unchanged. | settled |
| D8 | `templates/structure/specs-README.md` is not changed. | The PR stays out of the CI BLOCK tier. | settled |
| D9 | The design reviewer receives the template by path and Reads it, instead of the prompt copying the definitions. | One source for the definitions. No copy to drift (`docs/solutions/harness/prose-encoded-state-logic-accrues-contradiction-chains.md`). | settled |
| D10 | The change rule reaches post-approval sessions through a pointer line under `## Decisions` in every design, not through edits to `writing-plans` or `subagent-driven-development`. | No fourth skill in scope. The remaining gap is stated in `What we do not claim`. | settled |
| D11 | The §6.1 decision-change checks are kept and apply in a revision pass of an approved design (§5.3). | They are not dead code: revised designs exist. A `DC<n>` written during implementation waits for the next revision pass. | settled |
| D12 | Enforce through the two existing reviewer loops, and register `spec-document-reviewer-prompt.md` in `scripts/render_skill_prompt.py` `CONTEXT_MATRIX` (required token `design-template.md`, required Read of it). | One `scripts/` edit (CI warn tier). Delivery of the template to the isolated reviewer is checked by `--check-all` and a mutation test. No hook change; the reviewer judgment stays judgment-tier. | settled |

## Decision changes

- DC1 — 2026-10-08 — reopens D1 — evidence: research brief (Local, 2026-10-08): `scripts/render_skill_prompt.py` `CONTEXT_MATRIX` is the canonical delivery contract for isolated-subagent prompts, and `spec-document-reviewer-prompt.md` is the only reviewer prompt not registered; its `Read` regex also catches a deleted Read that the §7 anchor grep misses. The user chose to register it (2026-10-08) — new decision: D12
