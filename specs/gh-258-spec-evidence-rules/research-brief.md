# Research Brief — gh-258-spec-evidence-rules

Written 2026-10-08. Pins: agent-harness `b0d2a92` (VERSION 2.28.0). Depth: **Deep** (intake lane
high-risk → Deep per `rules/research-depth.md`; re-run with evidence below, no change).

---

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing: the xia2 template pattern, the two reviewer loops, the per-skill contract tests |
| **Why this is the lightest credible path** | Every unit in the approved design maps onto an existing file and an existing pattern. Nothing new is needed except one reference file. |
| **Confidence** | 85% |
| **Next step** | `writing-plans`. F1 resolved: register the design reviewer (DC1 → D12, 2026-10-08). F2 adopted: per-skill contract test files. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Skill framework / workflow-as-code meta-repo (Markdown skills, Bash hooks, Python scripts) |
| Primary language + runtime | Markdown prose; Bash; Python 3 (stdlib only for the scripts touched here) |
| Frameworks / platforms | Claude Code skills (`skills/<name>/SKILL.md`), Codex advisory alpha via `adapters/codex/` |
| Relevant packages | none |
| Detectable versions | `VERSION` 2.28.0 |
| Important constraints | `CLAUDE.md` gate verifiability (Verifies / Does not verify); `rules/terminology.md` "Delivery" (write-flows need an explicit Read) and §2 (a word does not force a step); `ci-strict-gate.sh` BLOCK tier = `hooks/`, `settings.json`, `templates/`, `render_plan.py`; `workflow-engine` signal (warn) on `skills/*` |

---

## Feature Understanding and Assumptions

- **Requested feature:** items 1, 2 and 4 of #258, as specified in the approved `design.md`.
- **What success appears to mean:** design §8. The contract test exits 0 with the §7 anchors, and the full suite passes.
- **Assumptions from the request:** the design is approved and settled (D1–D11). This brief does not reopen it.
- **Assumptions still needing confirmation:** F1 and F2 below. Both would touch settled decisions, so after approval they are Rule 4 questions for the user, not research choices.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `skills/brainstorming/SKILL.md` step 5 (line ~33): "Write the approved result to `specs/<slug>/design.md`. Then read `references/spec-review-loop.md` and complete its review/user-review gates." This is the insertion point for the explicit Read of `references/design-template.md`. |
| `Local` | `skills/brainstorming/references/spec-review-loop.md` step 1: "Dispatch `spec-document-reviewer-prompt.md` with the design path and the design text, never the parent session history." The template path is added here. |
| `Local` | `skills/brainstorming/spec-document-reviewer-prompt.md`: a fenced `Task tool (general-purpose)` prompt with a `What to Check` table (7 rows) and a `Commonly missed` list. It has one placeholder, `[SPEC_FILE_PATH]`. New rows and `[TEMPLATE_FILE_PATH]` go inside the fence. |
| `Local` | `skills/writing-plans/SKILL.md` step 5: "Run `python3 scripts/check_plan_contract.py specs/<slug>/PLAN.md`, read `references/review-loop.md`, review the plan, and save it. Then run `python3 skills/visual-planner/render_plan.py …`". The coverage step goes first in step 5, before the contract check (design §4). |
| `Local` | `skills/writing-plans/plan-document-reviewer-prompt.md`: already passes `**Spec for reference:** [SPEC_FILE_PATH]` and a `What to Check` table. The Assumption-coverage row is added there. It already has explicit Reads of `rules/plan-format.md` and `rules/terminology.md`. |
| `Local` | `skills/xia2/references/research-brief-template.md`: `## Evidence Ledger` with labels `Local`/`Upstream`/`Docs`/`Inference`. The number-label rule goes next to it. |
| `Local` | `skills/compound/SKILL.md` (54 lines): `## Extract and select` has a track table (bug/knowledge/decision/failure). The prediction → measured line belongs in that section. |
| `Local` | Contract tests already exist per skill: `tests/scripts/brainstorming-contract.test.sh` (3 checks), `writing-plans-contract.test.sh` (3), `compound-contract.test.sh` (3). All use `grep -q` on `$ROOT/<file>`, with `t`/`pass`/`fail`/`finish` from `tests/lib.sh`. |
| `Local` | `tests/scripts/compound-contract.test.sh` pins `| bug |` … `| failure |`, `scripts/rebuild_solution_index.py`, `Do not manually scan/sort/render`, `critical-patterns.md`, `proposed:`. The compound edit must not remove any of these. |
| `Local` | `tests/scripts/writing-plans-contract.test.sh` pins `Read \`rules/plan-format.md\``, `design.md`, `research-brief.md`, `using-git-worktrees`, `subagent-driven-development`. |
| `Local` | `tests/scripts/research-depth-drift.test.sh` pins five phrases in `research-brief-template.md` (`external surface`, `upgrades a dependency`, `integrates an external system`, `version-specific API`, `local-only`) and parses the `## Docs Findings` section by heading. The new label text must not rename `## Docs Findings` and should not repeat those phrases. |
| `Local` | `scripts/render_skill_prompt.py` `CONTEXT_MATRIX` is the canonical delivery contract for isolated-subagent prompts. It lists `plan-document-reviewer`, `task-reviewer`, the correctness prompts, and others. **`spec-document-reviewer-prompt.md` is not registered.** `--check-all` asserts each `required` token is in the prompt, and `context-propagation-regression.test.sh` mutation-tests two entries. |
| `Local` | `scripts/deploy-harness.sh` `rewrite_derived_paths()` rewrites only `scripts/<consumer helper>`, `harness-manifest.json` and `python3 skills/visual-planner/render_plan.py` in derived Markdown. Skill-relative `references/…` paths are not rewritten and need no rewrite. They resolve against the skill's base directory in both the harness repo (`skills/brainstorming/`) and a consumer (`.claude/skills/brainstorming/`). |
| `Local` | `scripts/test_check_skill_tool_conformance.py` covers the brainstorming shape: a dispatch declared in a `references/` loop file requires `Agent` or `Task` in `allowed-tools`. Brainstorming already grants `Read, Write, Grep, Glob, Agent, Task`, so no tool change is needed. |
| `Local` | `scripts/generate_skill_eval_corpus.py` describes brainstorming by intent phrases ("design approval before code", "handoff xia2 then writing-plans"). The change does not affect it. |
| `Local` | `adapters/codex/project/harness-instructions.md`: Codex gets skills through the Agent Harness plugin. No adapter file names `brainstorming` or `spec-document-reviewer`, so no regeneration is needed. |
| `Local` | `skills/visual-planner/render_plan.py` lines 1140–1232: `render_risks()` cards only the first bullet list, and the list ends at a blank line. `split_sections` splits on `^##\s+`. This confirms design §5.5 and A5. |
| `Upstream` | `tamnd/rupg/spec` (reviewed for #258): `00-README.md` "Settled decisions" (change only after a measurement in doc 24); `02-the-goal.md` §2.4.4 H1–H6, §2.9, §2.10; `24-open-questions.md` closed and open register. |
| `Upstream` | ADR practice (MADR-derived templates and team ADR wikis): status `superseded` plus a link to the replacing record; accepted records are immutable, and a change is a new record. This matches design §5.3 (old row kept as `superseded by DC<n>`, new `D<n>` row). |
| `Inference` | The number-label rule is stated in two files (design template and research-brief template). That is the inline-policy-copy shape the repo guards with drift tests (`inline-policy-drift`, `research-depth-drift`). Design §7 checks 2 and 5 grep the same label string in both files, which works as a traceability-tier drift guard for the label set. |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** the eight files in design §4, plus `writing-plans-contract.test.sh`, `compound-contract.test.sh`, `research-depth-drift.test.sh`, `context-propagation-regression.test.sh`, `scripts/render_skill_prompt.py`, `scripts/test_check_skill_tool_conformance.py`.
- **Existing abstractions or extension points:** the xia2 `references/<template>.md` output-contract pattern; reviewer-prompt placeholders (`[SPEC_FILE_PATH]`, `[PLAN_FILE_PATH]`); per-skill `*-contract.test.sh`; `CONTEXT_MATRIX` for delivery to isolated subagents.
- **Conventions worth preserving:** explicit **Read** for anything an isolated or write-flow context needs; a `Verifies:` / `Does not verify:` header on tests that guard policy; multi-word anchors that occur only in the rule text (the `research-depth-drift` lesson: the stems `depend` and `integrat` were vacuous).
- **What can likely be reused:** the `t`/`pass`/`fail` test harness and its grep style; the research-brief template's structure as the model for `design-template.md`.
- **What appears missing locally:** a design template (expected; the design creates it); a `CONTEXT_MATRIX` entry for the design reviewer (F1).

---

## Upstream Findings

- **Repositories inspected:** `tamnd/rupg` (`spec/`, shallow clone at its `main` on 2026-10-08, commit `d905f5e`); ADR template conventions via web search.
- **Pattern or capability already present upstream:** assumption hypotheses with evidence (H1–H6), negative claims (§2.9), immutable settled decisions changed only by an evidence entry, and the superseded-by status convention.
- **Files, modules, or areas worth modeling:** `rupg/spec/02-the-goal.md` §2.4.4 and §2.9; `rupg/spec/24-open-questions.md` §24.1 (closing rules).
- **How closely the upstream pattern matches this repo:** close on intent, different in mechanism. rupg relies on discipline in one large human-maintained corpus. This repo relies on reviewer subagents per spec. The design already adapts for that difference.
- **Any upstream gaps or uncertainties:** the exact MADR 4.x front-matter syntax was not confirmed from the official repository. That does not matter here, since only the status convention is borrowed.

---

## Docs Findings

- none (local-only; no external surface). The change edits skill prose and tests only. It adds no dependency, integrates no external system, and relies on no version-specific API.

---

## Recommendation

- **Primary recommendation:** reuse existing. Implement design §4 as written, with these plan-level details:
  1. `design-template.md` mirrors the research-brief template's shape: a short "use this template" header, then the sections. The four new sections go after Non-goals with the rules of §5.1–§5.4, including the reopen pointer line under `## Decisions`.
  2. Insert the template Read into brainstorming step 5 before "Write the approved result". Add the template path to `spec-review-loop.md` step 1. Add `[TEMPLATE_FILE_PATH]` and a Read instruction inside the reviewer prompt's fence.
  3. Put the number-label rule in `research-brief-template.md` directly under the `## Evidence Ledger` intro line. Leave `## Docs Findings` and the five drift phrases untouched.
  4. Add the compound line in `## Extract and select`, without touching the five pinned anchors.
- **Why this is the lightest credible path:** every edit lands in an existing file and pattern (Evidence Ledger rows), except the one new template, which follows the xia2 precedent.
- **Why the next-best alternative lost:** building a lint (design approach C) was rejected in the design (D1). Nothing here changes that.
- **What would change this recommendation:** a "yes" on F1. Adding a `CONTEXT_MATRIX` entry is a small `scripts/` edit that turns the delivery claim from audit-only into a mechanically checked contract with a mutation test.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - R1. `research-depth-drift.test.sh` parses the brief template by heading. A renamed `## Docs Findings`, or a repeated drift phrase, breaks it or makes it vacuous. Mitigation: insert text only inside `## Evidence Ledger`, and run that test in the plan's Verify.
  - R2. `compound-contract.test.sh` and `writing-plans-contract.test.sh` pin anchors in files the plan edits. Mitigation: run both tests in Verify.
  - R3. Without a `CONTEXT_MATRIX` entry, nothing mechanical detects a later removal of the design reviewer's template Read. Only the contract-test anchor (design §7 check 3) and the audit catch it. See F1.
- **Evidence gaps:** whether a reviewer subagent applies the "load-bearing" definition reliably (design A2). That is judgment-tier until the post-implementation dry run.
- **Version uncertainties:** none.
- **Follow-up questions for the user** (both resolved 2026-10-08 — F1: yes, recorded as DC1/D12 in `design.md`; F2: per-skill files, applied to design §7):
  - **F1.** Register `spec-document-reviewer-prompt.md` in `scripts/render_skill_prompt.py` `CONTEXT_MATRIX` with `required: ["design-template.md"]` and `required_reads: [...]`? It is the canonical delivery guard for isolated prompts and covers exactly what design A1 and A3 leave at "audit only". But it edits `scripts/` (CI warn tier), and D1 settled "no change under `scripts/`". After approval that needs a `DC1` entry, so this is the user's call.
  - **F2.** Design §7 puts the writing-plans, xia2 and compound anchors in `brainstorming-contract.test.sh`, with a comment. `writing-plans-contract.test.sh` and `compound-contract.test.sh` already exist and are where a reader would look. Moving those anchors is a plan-level detail inside §7's text, not a `D<n>` row. The plan can take either. This brief recommends the per-skill files.

---

## Source Pack

- **Local files read:** `skills/brainstorming/SKILL.md`; `skills/brainstorming/references/spec-review-loop.md`; `skills/brainstorming/spec-document-reviewer-prompt.md`; `skills/writing-plans/SKILL.md`; `skills/writing-plans/references/review-loop.md`; `skills/writing-plans/plan-document-reviewer-prompt.md`; `skills/xia2/references/research-brief-template.md`; `skills/compound/SKILL.md`; `tests/scripts/brainstorming-contract.test.sh`; `tests/scripts/writing-plans-contract.test.sh`; `tests/scripts/compound-contract.test.sh`; `tests/scripts/research-depth-drift.test.sh`; `tests/scripts/context-propagation-regression.test.sh`; `tests/scripts/inline-policy-drift.test.sh`; `scripts/render_skill_prompt.py`; `scripts/deploy-harness.sh` (`rewrite_derived_paths`); `scripts/test_check_skill_tool_conformance.py`; `scripts/generate_skill_eval_corpus.py`; `scripts/lint-doc-truth.sh`; `skills/visual-planner/render_plan.py` (1140–1232); `adapters/codex/project/harness-instructions.md`; `rules/research-depth.md`; `rules/terminology.md`; `specs/ste-terminology-evidence/DECISION.md`
- **Upstream repositories or pages checked:** https://github.com/tamnd/rupg/tree/main/spec ; https://io-docs.feyenoord.com/architecture/decisions/ ; https://smithery.ai/skills/claylo/capturing-decisions
- **Official docs:** none (local-only; no external surface)
