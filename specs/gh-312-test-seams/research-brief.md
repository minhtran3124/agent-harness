# gh-312-test-seams — Research Brief

Written 2026-10-16. Pins: repo 38c7bfe

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | Reuse existing: extend `scripts/check_plan_contract.py`, `scripts/check_task_review_contract.py` and the two SDD prompts; adapt the seam vocabulary from upstream `mattpocock/skills` (`to-spec`, `tdd`) |
| **Why this is the lightest credible path** | Every delivery path already exists: the brief copies the whole task block and `## Global Constraints`, both parsers fold an unknown bullet into the field before it, and the checker already has an opt-in gate to extend |
| **Confidence** | 85% |
| **Next step** | `writing-plans`: one plan with a checker wave, a prompt wave, and a proof wave (canary + gh-175 replay) |

Depth: **Deep** (intake lane `high-risk`). No upgrade needed. No external surface: no dependency
is added or upgraded, and no external system or version-specific API is used.

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Claude Code skill framework and workflow harness (meta-repo, no application stack) |
| Primary language + runtime | Markdown prompts; Python 3 scripts; Bash hooks and tests |
| Frameworks / platforms | Claude Code skills, subagents, hooks; pytest for Python tests |
| Relevant packages | none (stdlib `re`, `argparse`, `pathlib` only in the touched scripts) |
| Detectable versions | no manifest pins the touched scripts; `techstacks/` is empty by design |
| Important constraints | `scripts/ste-baseline.json` holds both SDD prompts, `rules/plan-format.md` and `skills/writing-plans/SKILL.md` at 0 hard STE findings; `scripts/` changes are in the warn tier of `scripts/ci-strict-gate.sh`; `skills/subagent-driven-development/SKILL.md` is at 600/600 words |

---

## Feature Understanding and Assumptions

- **Requested feature:** issue #312 as amended by the approved intent (`2cd6403`) and design
  (`38c7bfe`): a `- **Seams:**` task field, a `- Plan-contract: 2` opt-in marker, a blocking
  checker rule, implementer test rules, a reviewer seam check, a phrase pin, and a canary proof.
- **What success appears to mean:** design SC-1 to SC-8.
- **Assumptions from the request:** the design's decisions D1–D16 are settled.
- **Assumptions still needing confirmation:** none that changes the recommendation. One
  checker detail follows from D1 and is new evidence (see Risks: field order).

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `skills/subagent-driven-development/scripts/task_brief.py:23,56` copies `## Global Constraints` and the whole task block into the brief, so the marker and `Seams:` reach both subagents with no script change (design A1) |
| `Local` | `skills/visual-planner/render_plan.py:243-262` and `runtime/resume_decision.py:46-49,209-216` use the same field regex; a bullet with an unknown name is appended to the field before it. After `Interfaces`, `Seams:` text joins the Interfaces value (design A2, A3 now provenance) |
| `Local` | The same parsers would append a `Seams:` bullet placed after `Verify` to the Verify command, which `resume_decision.py` re-runs as `checks_to_rerun` (Inference from the shared fold rule at `resume_decision.py:209-216`) |
| `Local` | `scripts/check_plan_contract.py:51-89`: opt-in by `## Global Constraints`; `FIELD` regex reads `Criteria` and `Interfaces` one line each; a marker bullet also satisfies "Global Constraints must contain at least one bullet" |
| `Local` | `scripts/check_task_review_contract.py` checks 6 fixed strings in `task-reviewer-prompt.md` only; `scripts/test_check_task_review_contract.py` mutates a copy under `tmp_path` and asserts exit 1 — the pattern to reuse for the implementer pins |
| `Local` | `scripts/test_check_task_review_adoption.py` runs `check_task_review_adoption.py`, which runs the checker on `specs/superpowers-6-review-pipeline-adoption/PLAN.md` |
| `Local` | Existing phrase anchors that the prompt edits must keep: `tests/scripts/context-propagation-regression.test.sh` (`FIRST: Read .*auto-correct-scope\.md` in the implementer prompt; `Spec verdict also covers scope`, `**Files:**`, `Ignore bookkeeping paths` in the reviewer prompt); `tests/scripts/sdd-artifact-handoffs.test.sh` (`do not write a report file`, `Fix round`); `scripts/test_verify_summary.py:1179-1202` (red-row command template and `Input type: [INPUT_TYPE]`); `tests/scripts/runtime-entry-bindings.test.sh:90` (`model_stage: task_reviewer`) |
| `Local` | `scripts/render_skill_prompt.py:28,32` and `scripts/run_review_prompt_eval.py:117` render the two prompts by path; they do not pin prompt text |
| `Local` | `harness-manifest.json:73` contract `artifact-schema-plan`: surface `rules/plan-format.md`, `scripts/check_plan_contract.py`; consumers `render_plan.py`, `writing-plans/SKILL.md`, `subagent-driven-development/SKILL.md`. `scripts/check-contract-impact.sh` is advisory (exit 0) |
| `Local` | `skills/writing-plans/plan-document-reviewer-prompt.md:32-33` checks Success Criteria and decidable criteria; it has no row for `Interfaces` or seams |
| `Local` | `task-reviewer-prompt.md:28-30` allows "one named, focused read-only search" and bans broad crawling (design D15 adds the seam allowance) |
| `Local` | 36 (measured 2026-10-16, `grep -l '^## Global Constraints' specs/*/PLAN.md`) contract plans; the spec reviewer ran the checker on each, all exit 0 |
| `Local` | `adapters/` holds no reference to the touched files (`rg` for `subagent-driven-development`, `writing-plans`, `plan-format` returned nothing), so the Codex adapter needs no regeneration |
| `Upstream` | `mattpocock/skills@49dd158` `to-spec/SKILL.md` step 2: "Existing seams should be preferred to new ones. Use the highest seam possible ... the ideal number is one." (via `research_notes/Lessons from Matt Pocock skills/pocock_skill_contents.md:65`) |
| `Upstream` | `tdd/SKILL.md`: "No test is written at an unconfirmed seam"; "Give each proposed seam a one-line note on what it catches and what it misses"; implementation-coupled and tautological anti-patterns with the "independent source of truth" wording (`pocock_skill_contents.md:83`) |
| `Upstream` | `docs/engineering/tdd.md`: "`/code-review` checks that only agreed-upon test seams were used" (`pocock_skill_contents.md:139`) |
| `Inference` | Upstream has no real-input (corpus) rule; D6 comes from the local record `docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md`, not from upstream |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** `rules/plan-format.md:44-54`;
  `skills/writing-plans/SKILL.md:26-29`; `scripts/check_plan_contract.py`;
  `scripts/test_check_plan_contract.py` (9 tests); `skills/subagent-driven-development/
  implementer-prompt.md:44-58`; `task-reviewer-prompt.md:28-30,56-62`;
  `scripts/check_task_review_contract.py` and its test; the four phrase-anchor tests in the
  Evidence Ledger.
- **Existing abstractions or extension points:** the checker's opt-in early return and its
  per-task `fields` loop; `FIELD` regex (add `Seams`); `REQUIRED` tuple in
  `check_task_review_contract.py` (add an implementer tuple); `mask_fences` already handles
  fenced examples, which covers the "marker in a fence" row.
- **Conventions worth preserving:** one message line per problem in the form
  `<name>: Task <id> ...`; exit 0/1; tests that mutate a copy in `tmp_path`; STE 0-hard-finding
  baselines; the red/green prose anchors.
- **What can likely be reused:** all delivery paths (brief, renderer, resume); the
  `test_check_task_review_contract.py` mutation pattern; the corpus-test idea already used in
  `runtime/test_resume_decision.py` (`test_corpus_parity_parse_tasks_matches_render_plan`).
- **What appears missing locally:** a seam field and checker rule; implementer test-location
  and expected-value rules; a reviewer seam check; an implementer phrase pin; a corpus test for
  `check_plan_contract.py`.

---

## Upstream Findings

- **Repositories inspected:** `mattpocock/skills` at `49dd158` (2026-10-09), through the local
  research notes `research_notes/Lessons from Matt Pocock skills/` written for the roadmap.
- **Pattern or capability already present upstream:** seams are agreed in the spec step,
  enforced in `tdd` ("No test is written at an unconfirmed seam"), and checked in `code-review`.
  Each seam has a one-line catches/misses note. Expected values come from an independent source.
- **Files, modules, or areas worth modeling:** `to-spec` step 2 wording for the plan rule
  (prefer existing seams, highest seam possible, ideal number one); `tdd` anti-pattern wording
  for the implementer rules.
- **How closely the upstream pattern matches this repo:** close in shape (plan → implementer →
  reviewer). Different in the confirmation step: upstream asks the user to confirm seams; here
  the plan review and the checker take that role, and the human is not a gate on the normal
  lane.
- **Any upstream gaps or uncertainties:** upstream has no mechanical check and no real-input
  rule; the notes are a secondary source (quoted from the repo at `49dd158`), not a fresh read.

---

## Docs Findings

No external surface: no dependency, external system or version-specific API is involved.

---

## Recommendation

- **Primary recommendation:** reuse existing. Extend the checker, the phrase pin and the two
  prompts. Copy the upstream wording "prefer existing seams; use the highest seam possible" into
  the `plan-format.md` seam definition, because it tells the plan author how to choose a seam,
  which the design does not yet say.
- **Why this is the lightest credible path:** no parser, renderer, brief or adapter change is
  needed (Evidence Ledger rows 1, 2, 13).
- **Why the next-best alternative lost:** a new `**Seams:**` parser field in `render_plan.py`
  and `resume_decision.py` would touch a high-blast file for display only; the fold rule
  already shows the text in the Interfaces cell.
- **What would change this recommendation:** SC-8 shows that the renderer drops or garbles the
  `Seams:` text, or the resume corpus parity test fails on this spec's own plan.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - **Field order.** A `Seams:` bullet placed after `Verify` would be appended to the Verify
    command by both parsers, and `resume_decision.py` re-runs that command. D1 already says
    "directly after `Interfaces`"; the checker should enforce it: a marker plan whose `Seams:`
    bullet does not directly follow the `Interfaces` bullet is rejected. This adds one row to the
    design's error table as an implementation of D1, not a new decision.
  - **STE baseline.** New prose in four files must keep 0 hard STE findings
    (`scripts/check_ste_baseline.py` runs in `run-tests.sh`).
  - **Phrase anchors.** The implementer edit sits next to the red/green block that
    `test_verify_summary.py` pins; the replacement must keep the red-row template verbatim.
  - **Canary is model judgement.** One sample can pass by chance; design budgets two failed runs
    before escalation.
- **Evidence gaps:** upstream wording is read from local notes, not re-fetched; whether the
  gh-175 replay can be dispatched with a faithful package (the original task reviewer did not
  run on `ba964a3..e76b0fe` as one task) is checked during the proof task.
- **Version uncertainties:** none (no versioned dependency).
- **Follow-up questions for the user:** none. A possible follow-up issue: add a seam-quality row
  to `plan-document-reviewer-prompt.md` (the checker verifies shape, not seam choice).

---

## Source Pack

- **Local files read:** `rules/plan-format.md`, `skills/writing-plans/SKILL.md`,
  `scripts/check_plan_contract.py`, `scripts/test_check_plan_contract.py`,
  `scripts/check_task_review_contract.py`, `scripts/test_check_task_review_contract.py`,
  `scripts/check_task_review_adoption.py`, `skills/subagent-driven-development/{SKILL.md,
  implementer-prompt.md,task-reviewer-prompt.md,scripts/task_brief.py,scripts/review_package.py}`,
  `skills/visual-planner/render_plan.py`, `runtime/resume_decision.py`,
  `tests/scripts/context-propagation-regression.test.sh`, `tests/scripts/sdd-artifact-handoffs.test.sh`,
  `scripts/test_verify_summary.py`, `harness-manifest.json`, `scripts/ste-baseline.json`,
  `scripts/check-contract-impact.sh`, `skills/writing-plans/plan-document-reviewer-prompt.md`,
  `docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md`,
  `specs/gh-175-executable-resume-cursor/SUMMARY.md`, `runtime/test_resume_decision.py@e76b0fe`
- **Upstream repositories or pages checked:** `https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/engineering/to-spec/SKILL.md`,
  `.../skills/engineering/tdd/SKILL.md`, `.../docs/engineering/tdd.md` — read through the local
  notes in `research_notes/Lessons from Matt Pocock skills/pocock_skill_contents.md`
- **Official docs domains or pages checked:** - none (local-only; no external surface)

---

## Evidence Boundary

> Confirmed from artifacts: brief copies the task block and Global Constraints; both parsers fold
> unknown bullets into the previous field; the checker's opt-in and one-line field regex; the
> phrase anchors and their files; 36 contract plans pass today; the adapter does not reference
> the touched files.
> Inferred from patterns: a `Seams:` bullet after `Verify` corrupts the re-run command (from the
> shared fold rule; not executed); upstream has no real-input rule (from the notes).
> Not checked: a live re-fetch of the upstream files; the gh-175 replay mechanics; consumer repos'
> in-flight plans.
