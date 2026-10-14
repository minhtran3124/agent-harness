# review-policy — Design

Written 2026-10-11. Pins: repo 33d6ed4

## Goal

Give the review passes one shared review policy (`rules/review-policy.md`) and rewrite every
review agent and skill so its wording is plain and easy to follow, without changing what any
reviewer does.

## Current state

- Each reviewer carries its own severity scale and "do not report" list:
  - task review: `Critical | Important | Minor` (`skills/subagent-driven-development/task-reviewer-prompt.md`);
  - correctness review: `P0–P3` plus the scorer threshold 75 (measured 2026-10-11 `review-config.json` `default_threshold`) (`skills/correctness-review/prompts/shared.md`, `correctness-scorer-prompt.md`). Finders do not score; the scorer runs later in a fresh context, and the controller records below-threshold findings as advisory (`correctness-review/SKILL.md` step 4);
  - intent review: `gap | drift | excess` (`skills/intent-review/intent-reviewer-prompt.md`).
- The style exclusion ("style is the quality reviewer's work") appears in `prompts/shared.md` (lines 41 and 69) and `intent-reviewer-prompt.md` (line 119); `correctness-review/SKILL.md` line 9 says "not style". `task-reviewer-prompt.md` has none, because style belongs to its quality verdict.
- `tests/scripts/rule-loading-tiers.test.sh` hardcodes the path-scoped rule set, and `CLAUDE.md` names it ("four path-scoped ones").
- Child prompts already receive a path-scoped rule by an explicit Read: `prompts/shared.md` reads `rules/auto-correct-scope.md`.
- In-scope files total 7,867 words (measured 2026-10-11 `wc -w` at 33d6ed4):
  - `agents/reviewer.md`, `agents/task-reviewer.md`;
  - `skills/correctness-review/` (`SKILL.md`, `correctness-reviewer-prompt.md`, `correctness-scorer-prompt.md`, `prompts/shared.md`, six `prompts/angles/*.md`);
  - `skills/intent-review/` (`SKILL.md`, `intent-reviewer-prompt.md`);
  - `skills/subagent-driven-development/task-reviewer-prompt.md` and `references/review-chain.md`;
  - `skills/context-propagation-audit/SKILL.md`.
- Contract tests pin strings in these files, among them:
  - `tests/scripts/intent-prompt-contract.test.sh`, `scorer-threshold-contract.test.sh`, `correctness-prompt-composition.test.sh`, `inline-policy-drift.test.sh`, `context-propagation-regression.test.sh`, `final-review-package-contract.test.sh`, `runtime-entry-bindings.test.sh`, `sdd-artifact-handoffs.test.sh`;
  - `scripts/check_task_review_contract.py`.
- `scripts/run_review_chain_eval.py` sends its own hardcoded prompt (`INSTRUCTIONS`), not the skill prompts, so the scripted review-chain benchmark does not measure these files.

## Approaches considered

1. **One spec, waves** (chosen). Wave 1 adds the policy and the rule-inventory updates; waves 2–3 rewrite the wording, and the wave that rewrites a prompt also adds its Read line or label field. Each review file is edited once, and each wave stays reviewable on its own.
2. **Two specs, two PRs.** Smaller PRs, but every prompt is edited twice, and the Read line added in the first is rewritten in the second.
3. **Paste the policy into each prompt.** No Read line is needed, but this contradicts the user's choice of a rules file, copies the text into four places, and grows the word count.

For proof of unchanged behavior, the user chose a per-file meaning-equivalence review. The
alternatives were:
- the manual review-chain protocol on five core fixtures (about 80–100 dispatches);
- a runner mode that loads the real prompts.

## Architecture

**`rules/review-policy.md`** is a new file. Its frontmatter is `paths: ["specs/*/SUMMARY.md"]`: it is never always-on, and it is injected into a session that reads a SUMMARY, which is where the controller records findings. Its text is stack-neutral because it deploys to consumers. It has four parts:

1. **Important or Nit.** This maps the existing scales onto one vocabulary and changes no blocking rule:

   | Reviewer | Important (enters a fix round) | Nit (listed, never blocks) |
   |---|---|---|
   | Task review | `Critical`, `Important` | `Minor` |
   | Correctness review | a finding scored at or above the threshold (any P0–P3) | a finding scored below the threshold (already advisory) |
   | Intent review | `gap`, and `drift` that changes behavior | equivalent `drift`; `excess` is report-only |

2. **Nit reporting.** There is no count cap. A Nit stays in the reviewer's existing findings list under its existing severity or class, so no report format changes. The controller never opens a fix round for a Nit and records it in SUMMARY as today. For correctness review the scorer threshold already does this routing; the policy only names it.
3. **Do not report:**
   - generated files (`PLAN.html`, `.plan-review.json`, deployed `.claude/` copies, `*.lock`);
   - lint and format findings that the project's linters or formatters already check (`agents/PROJECT.md` → Test execution);
   - for correctness review and intent review only: style, naming, and formatting, which belong to the task reviewer's quality verdict.
4. **Finding label:**
   - the task reviewer adds `checked_against: SC-n | none` to each finding;
   - intent review's required quote of the verbatim intent sentence is its label;
   - correctness review has no label because it is plan-blind.

**Delivery.** Three prompts gain one explicit `Read rules/review-policy.md` line, following the `auto-correct-scope.md` pattern:
- `task-reviewer-prompt.md`;
- `prompts/shared.md`, which reaches all six finders;
- `intent-reviewer-prompt.md`.

The scorer does not classify findings into Important or Nit (the threshold does), so it gets no
Read line; `correctness-reviewer-prompt.md` reaches the policy through `prompts/shared.md`. This
is how the intent's "each review prompt names the policy file" is met. The style lines in
`prompts/shared.md` and `intent-reviewer-prompt.md` move into the policy; `correctness-review/SKILL.md`
keeps its one-line scope statement. The explicit Read is the guaranteed channel to a fresh reviewer context; the `paths:` injection reaches only a session that reads a SUMMARY and is not counted as delivery.

**Rule-inventory updates.** Adding a fifth path-scoped rule requires updating
`tests/scripts/rule-loading-tiers.test.sh` (its contextual set) and the `CLAUDE.md` rule inventory
("four path-scoped ones" becomes five, with the file named), in wave 1.

**Rewrite.** Every in-scope file is rewritten against this checklist:
- complete imperative sentences;
- one word per concept;
- no invented shorthand;
- no repeated explanation across files;
- no rationale the model does not need in order to act;
- no CAPS or MUST emphasis for a rule a gate already enforces;
- no new step or rule.

The waves are:
- wave 1: `rules/review-policy.md`, `rule-loading-tiers.test.sh`, and `CLAUDE.md`;
- wave 2: agents, the three `SKILL.md` files, and `review-chain.md`;
- wave 3: the child prompts, each with its Read line (`task-reviewer-prompt.md`, `prompts/shared.md`, `intent-reviewer-prompt.md`) and the task reviewer's `checked_against` field, together with the checks for them: the new Read-line test and the `check_task_review_contract.py` update. A check lands in the same wave as the content it checks, so the suite is green after every wave.

Each reviewer keeps its oracle, inputs, output schema (apart from the new label field), finding
categories, and blocking rules. Strings pinned by contract tests stay. If a test pins wording
rather than meaning, it may change, and the change is recorded in `### Deviations`.

## Error behavior

- If a consumer's re-sync keeps a locally modified rule and writes the incoming policy beside it as `<file>.harness-incoming`, or the policy file is missing, the reviewer's Read fails. Each prompt still holds its own oracle and output schema, so the review runs without the shared vocabulary rather than failing. The Read-line test catches a missing file or Read line in this repo.
- If the meaning-equivalence review lists a dropped or changed instruction, the implementer restores it or the SUMMARY records why the loss is intended. An unexplained item blocks the wave.

## Tests

- **New test:**
  - `rules/review-policy.md` exists and has `paths:` frontmatter (traceability);
  - each of the three prompts contains the Read line (traceability).
  - This test lands in wave 3; during waves 1–2 the updated `rule-loading-tiers.test.sh` is what checks the policy file.
- **Updated:** `scripts/check_task_review_contract.py` requires `checked_against` in the task-reviewer output schema (traceability); `tests/scripts/rule-loading-tiers.test.sh` and `CLAUDE.md` list the new path-scoped rule (traceability).
- **Word count:** the in-scope files total at most 7,867 words (budget), excluding the policy file (truth: re-counted).
- **Full suite:** `bash scripts/run-tests.sh`, including `audit_skill_prompts.py` and the contract tests (truth).
- **Meaning-equivalence review:** for each rewritten file, an independent reviewer compares the base and new text and lists every dropped, changed, or added instruction (none (judgment); recorded in SUMMARY).
- **Context-propagation audit:** for the policy delivery to each reviewer context (workflow-engine gate).

## Success criteria

- `rules/review-policy.md` exists with `paths:` frontmatter and the four parts above.
- Each of the three prompts names the policy in a Read line, and the new test fails when one is removed.
- The task-reviewer output schema contains `checked_against: SC-n | none`, and `check_task_review_contract.py` requires it.
- The in-scope files total at most 7,867 words (budget), excluding the policy file.
- `rule-loading-tiers.test.sh` and `CLAUDE.md` list `review-policy.md` as path-scoped.
- `bash scripts/run-tests.sh` exits 0.
- Every rewritten file has a meaning-equivalence record with no unexplained item.

## Non-goals

- `/code-review` and the in-PR review loop (H4).
- Changing which findings block, the scorer threshold, or any severity scale.
- Redeploying `.claude/`.
- Changing `scripts/run_review_chain_eval.py`.

## What must be true

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | A fresh reviewer context follows an explicit Read of a path-scoped rule named in its prompt | provenance: Local, 2026-10-11, `prompts/shared.md` Read of `rules/auto-correct-scope.md`, guarded by `context-propagation-regression.test.sh` | context-propagation audit | The policy is not applied in child contexts; paste it instead with a drift test |
| A2 | Contract tests pin meaning-bearing strings, so keeping them keeps the contracts | none yet: Inference, 2026-10-11, test names | rewrite tasks run the suite before and after | A wording-only pin blocks a rewrite; change the test and record it in Deviations |
| A3 | The rewrite can stay at or under 7,867 words (budget) while adding the Read lines and the label field | none yet: Inference, 2026-10-11, repeated text such as the `model_stage` paragraph in three prompts | word-count check | Keep the original wording where cutting would drop meaning; report the overage |
| A4 | Moving the style exclusion into the policy keeps it in force for correctness and intent review | none yet: Inference, 2026-10-11, `prompts/shared.md` and `intent-reviewer-prompt.md` style lines plus the A1 Read pattern | context-propagation audit plus the Read-line test | Keep a one-line exclusion in each prompt |

## What we do not claim

| Guarantee a reader may expect | Why not |
|---|---|
| Review behavior is unchanged at runtime | No behavioral eval runs the rewritten prompts; the meaning-equivalence review is judgment, not a re-run |
| Consumers get the policy immediately | Consumers receive it on their next harness re-sync |
| The task reviewer's catch rate is unchanged | It has no behavioral fixture |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | One spec with waves: the policy and the rule-inventory updates first, then the rewrite, with Read lines added in the rewrite wave of each prompt | Each review file is edited once | settled |
| D2 | The policy lives in `rules/review-policy.md`, path-scoped, and is read explicitly | Three prompts gain a Read line | settled |
| D3 | Finding labels: task reviewer `checked_against`; intent review keeps its verbatim quote; correctness review is exempt | One schema field is added; plan-blindness is kept | settled |
| D4 | No cap on the number of Nits; they are listed and never block | `opus-5-5-prompt-audit` decision 2 stays in force | settled |
| D5 | Correctness review's Nit is its existing below-threshold advisory class, not P3; Nits stay in each reviewer's existing findings list | No blocking rule and no report format changes | settled |
| D6 | Unchanged behavior is shown by a per-file meaning-equivalence review, contract tests, and the word budget | No behavioral eval is run; the limit is stated in `### Not auto-verified` | settled |
| D7 | The style exclusion applies to correctness and intent review only; the task reviewer keeps style in its quality verdict | The task reviewer's job is unchanged | settled |
| D8 | Policy frontmatter is `paths: ["specs/*/SUMMARY.md"]` | Injected where the controller records findings, not into unrelated contexts | settled |
