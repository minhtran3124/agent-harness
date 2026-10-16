# gh-309-grilling-rounds — Research Brief

Written 2026-10-16. Pins: repo 2a5fc1d; mattpocock/skills 49dd158; Python 3.12.3

Depth: **Deep** (intake lane high-risk → Deep; no waiver). Re-run with evidence: no signal lowers
it, and none raises it further. External surface: none (a prose edit to one skill; the upstream
pattern is a source, not a dependency).

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | adapt upstream: Pocock's `grilling` procedure, rewritten inline into step 2 as the approved design states, with the sentences re-shaped so the STE linter passes |
| **Why this is the lightest credible path** | The procedure already exists and is measured upstream; locally nothing but `SKILL.md` pins step 2, so one hunk in one file carries the change |
| **Confidence** | 85% |
| **Next step** | `writing-plans`: one rewrite task whose acceptance is the STE linter at zero new hard violations and the word ceiling, then the blind-run task using the `Explore` agent type for the grilling role, then the review chain |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Skill framework for Claude Code (markdown skills, bash hooks, python scripts) |
| Primary language + runtime | Markdown prose; Python 3.12.3 for scripts; bash for hooks |
| Frameworks / platforms | Claude Code skills; harness version 2.31.2 (`VERSION`) |
| Relevant packages | none (stdlib scripts) |
| Detectable versions | `VERSION` 2.31.2; `scripts/ste-baseline.json` pins `skills/brainstorming/SKILL.md: 1` |
| Important constraints | 600-word ceiling (`scripts/audit_skill_prompts.py`); STE structural rules (`skills/asd-ste100/SKILL.md`: ≤20 words per instruction, ≤25 per description, no semicolon); `workflow-engine` hard gate on `skills/*/SKILL.md`; brainstorming's only valid next skills are `xia2` → `writing-plans` (`skills/README.md:159`) |

---

## Feature Understanding and Assumptions

- **Requested feature:** rewrite step 2 of `skills/brainstorming/SKILL.md` so the agent grills the
  frontier of a design tree in numbered rounds with a recommended answer per question, finds facts
  itself, gives decisions to the user, and acts only after confirmation (`intent.md` @ 2bc2cb2,
  `design.md` @ 2a5fc1d, D1–D11).
- **What success appears to mean:** SC-1…SC-6 in `design.md`: seven behaviors present, skill under
  600 words, STE lint clean against the `996f50d` baseline, every dropped condition word cited,
  blind run closes the frontier in ≤3 rounds (budget) with no fact or implementation question, no
  other file under `skills/brainstorming/` changes.
- **Assumptions from the request:** the design's 169-word draft is the content, not the final
  wording (the design says the prose follows STE); the blind run is proof "(assumed)", the live
  session after merge is the real measure.
- **Assumptions still needing confirmation:** none that change the recommendation. One changes
  the plan: the draft must be re-shaped to pass the STE linter (see Local Findings).

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `skills/brainstorming/SKILL.md` is 442 words (measured 2026-10-16 `wc -w`), step 2 lines 22–26 is 64 words. The 169-word draft spliced in makes 547 words (measured 2026-10-16 `wc -w` on a scratch copy), under the 600 budget. |
| `Local` | STE linter on the base file: 3 violations, 2 hard (line 3 description 53 words, line 47 passive). On the scratch copy with the draft step 2: 7 violations, 6 hard. New ones: three `semicolon` (lines 23, 27, 31) and one `long-sentence` 28 words (line 26). `scripts/check_ste_baseline.py --strict --against 996f50d` would therefore exit 1 on the draft as written. (measured 2026-10-16, `python3 skills/asd-ste100/scripts/ste-lint.py`) |
| `Local` | Grep for "clarifying question" and "evasive" over `skills/ rules/ hooks/ scripts/ tests/ evals/`: only `skills/brainstorming/SKILL.md` and an unrelated xia2 scenario (`skills/xia2/tests/behavioural/pressure-scenarios.md:104`). No test pins step 2. |
| `Local` | Consumers of `brainstorming`: `skills/feature-intake/SKILL.md:66` (route), `skills/README.md:33,70,107,158,159,186` (inventory, handoff map), `harness-manifest.json:230` (skills list). None describes step 2's rhythm, so none needs an edit; the context-propagation audit confirms. |
| `Local` | `docs/solutions/harness/skill-eval-blind-run-scoring.md` (confirmed 2026-07-17): blind runs need a labeled fixture, the key never shown to the run, the first scored run is the record, and one run hides non-determinism (multi-run advised). |
| `Local` | `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md`: `SendMessage` follow-ups to idle subagents got no reply; silence is not a result. The design's relay restart fallback covers it. |
| `Local` | Agent roles (`agents/runtime-bindings.json`): `reviewer` = Glob/Grep/Read/Bash, no Agent; `task-reviewer` = Glob/Grep/Read; `coding` = runtime default incl. nested delegation. The session also lists an `Explore` agent type: all tools except Agent, Edit, Write. `Explore` matches the grilling role in the design (find facts yourself, no nested dispatch, no writes). |
| `Local` | `docs/research/harness-review-improvements/2026-06-15-brainstorm-improvements-synthesis.md` §1.1 proposed a "product pressure test" (four gap lenses) under step 2. It was never shipped and is out of scope here; the new step 2 does not block it later. |
| `Local` | `specs/brainstorming-gate-fix/SUMMARY.md` (tiny lane): the last edit to this skill removed the "every project" claim so `feature-intake` stays the routing authority. The new step 2 keeps that: it changes the rhythm inside the skill, not when the skill runs. |
| `Upstream` | mattpocock/skills @ 49dd158 `skills/productivity/grilling/SKILL.md` (30 lines, read verbatim via `gh api`): design tree; frontier = "every decision whose prerequisites are already settled"; "Ask the whole frontier in one round: number each question and give your recommended answer. Then wait"; fixed `❓/➡️` format; "Word each question so 'yes' accepts your recommended answer"; "A question whose answer depends on another question still open in this round belongs to a later round"; "Finding facts is your job, never the user's … dispatch a sub-agent … Don't block on it"; "The decisions are the user's: put each to them and wait"; "done when the frontier is empty … Do not act on it until the user confirms". |
| `Upstream` | mattpocock/skills `CHANGELOG.md` @ 49dd158, PR #593 (`a4b2009`): "Rework grilling from one-question-at-a-time to round-by-round … Same 13 questions land in ~3 rounds instead of 13." The number is the upstream author's report, not a reproducible measurement; it is the source of this issue's 3-round budget. Also notes an opt-out for one-question-at-a-time in the user's global `CLAUDE.md`. |
| `Upstream` | Same changelog, PR #917 (`---` between questions) and #879 (em-dashes replaced by colons and semicolons). The upstream text relies on semicolons, which STE bans; the local rewrite must not copy that punctuation. |
| `Inference` | A 547-word skill with step 2 at ~170 words reads unevenly next to steps of 20–60 words. Not a defect under any check; recorded in the design's approach table as the cost of approach A. |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** `skills/brainstorming/SKILL.md` (target);
  `skills/brainstorming/references/{design-template,spec-review-loop}.md` and
  `spec-document-reviewer-prompt.md` (unchanged); `skills/asd-ste100/scripts/ste-lint.py` and
  `scripts/check_ste_baseline.py` (lint); `scripts/audit_skill_prompts.py` (ceiling);
  `scripts/check_scope_qualifiers.py` (condition words); `docs/solutions/harness/deletion-test-for-word-ceiling.md`
  (if over budget); `evals/skills/task-review/*` (blind-run tooling pattern, not reused directly).
- **Existing abstractions or extension points:** the step list in `## Flow` is the only seam; step
  2 is replaced whole. The `Explore` agent type is the ready-made grilling role for the blind run.
- **Conventions worth preserving:** one instruction per sentence, no semicolons, ≤25 words
  (`skills/asd-ste100/SKILL.md`); whole-sentence deletions with each dropped condition word cited
  (`check_scope_qualifiers.py`, #308's `qualifiers-*.md` shape); `feature-intake` stays the
  routing authority (`specs/brainstorming-gate-fix`).
- **What can likely be reused:** the #308 `qualifiers-brainstorming.md` citation format; the
  blind-run integrity rules from `skill-eval-blind-run-scoring.md` (fixture, hidden key, first run
  is the record); the design's answer-key idea maps onto that entry's `truth.md`.
- **What appears missing locally:** nothing structural. The draft text itself needs four edits
  before it can ship: split the three semicolon sentences and the 28-word sentence (lines 23, 26,
  27, 31 of the scratch copy). A re-shaped draft that passes the linter is the implementer's first
  acceptance check, before the word count.

---

## Upstream Findings

- **Repositories inspected:** mattpocock/skills @ `49dd158` (`skills/productivity/grilling/SKILL.md`,
  `CHANGELOG.md`).
- **Pattern or capability already present upstream:** the whole procedure; also two details the
  design drops on purpose: the `❓/➡️` format (D3) and "don't block on a running sub-agent"
  (facts found inline here; nested dispatch is absent in the blind run and rare in a Claude Code
  brainstorm).
- **Files, modules, or areas worth modeling:** the sentence "A question whose answer depends on
  another question still open in this round belongs to a later round" is the clearest statement of
  the frontier rule; the design's draft says it as "Repeat with the new frontier". The implementer
  may use the upstream phrasing if it fits the word budget.
- **How closely the upstream pattern matches this repo:** closely for behaviors 1–7. Mismatches:
  upstream grilling is a standalone, model-invoked skill with no step 3–5 after it; here step 2
  sits inside a six-step flow, so the tier boundary (D4) is local and has no upstream equivalent.
- **Any upstream gaps or uncertainties:** the "13 questions in ~3 rounds" number is self-reported
  in a changelog; no fixture or transcript is published. The local blind run is the first
  measurement in this repo.

---

## Docs Findings

- none (local-only; no external surface). The change edits prose in one skill and depends on no
  dependency, external system, or versioned API.

---

## Recommendation

- **Primary recommendation:** adapt upstream, as the approved design already decided (D11,
  approach A). Research adds one plan-level constraint: the implementer rewrites the draft's four
  offending sentences so `ste-lint.py` reports zero new hard violations, then checks the word count.
- **Why this is the lightest credible path:** the procedure is proven upstream (changelog #593),
  nothing local pins step 2, and the full change is one hunk in one file plus spec records. The
  blind run needs no new tooling: `Explore` for the grilling role, any agent for the user role,
  `SendMessage` relay, a markdown record.
- **Why the next-best alternative lost:** a reference file (approach B) would not be read on
  every run and adds an STE-baseline entry; building a scored eval under `evals/` (per
  `skill-eval-blind-run-scoring.md`) would be the rigorous path but is out of scope for #309's
  single-run proof and would need a scorer for free-text rounds.
- **What would change this recommendation:** a re-shaped draft that cannot state all seven
  behaviors under 600 words without semicolons; then the deletion test applies to other steps, or
  approach B is reopened with a `DC`.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:** (1) STE lint fails on the draft as quoted in `design.md`; mitigated by
  making the linter the task's first acceptance check. (2) One blind run may pass or fail by
  chance (`skill-eval-blind-run-scoring.md` §5); the design budgets one run and two rerun cycles.
  A second run on the same key, if the plan has room, strengthens SC-5 without reopening any
  decision. (3) The grilling agent may ignore a step 2 handed to it without the surrounding skill
  (A3); the fallback is in the design. (4) `996f50d` is the merge-base today; if `sdlc` moves before
  the PR, re-check `git merge-base HEAD sdlc` for the qualifier and STE commands.
- **Evidence gaps:** no local measurement of rounds exists before this change (the issue's
  "instead of 13" is upstream's claim). The first real session after merge stays the only live
  evidence (A4).
- **Version uncertainties:** none.
- **Follow-up questions for the user:** none; no answer would change the recommendation.

---

## Source Pack

- **Local files read:** `skills/brainstorming/SKILL.md`; `skills/brainstorming/references/design-template.md`;
  `skills/brainstorming/references/spec-review-loop.md`; `skills/brainstorming/spec-document-reviewer-prompt.md`;
  `skills/asd-ste100/SKILL.md`; `skills/asd-ste100/scripts/ste-lint.py` (run); `scripts/check_ste_baseline.py` (run);
  `scripts/audit_skill_prompts.py` (run); `scripts/ste-baseline.json`; `harness-manifest.json`;
  `skills/README.md`; `skills/feature-intake/SKILL.md`; `rules/orchestration.md`;
  `agents/runtime-bindings.json`; `agents/reviewer.md`; `agents/coding.md`;
  `docs/solutions/INDEX.md`; `docs/solutions/critical-patterns.md`;
  `docs/solutions/harness/skill-eval-blind-run-scoring.md`;
  `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md` (via critical-patterns);
  `docs/research/harness-review-improvements/2026-06-15-brainstorm-improvements-synthesis.md`;
  `specs/brainstorming-gate-fix/SUMMARY.md`; `specs/gh-308-deletion-test-ceiling/{design,SUMMARY}.md`;
  `specs/gh-309-grilling-rounds/{intent,design}.md`.
- **Upstream repositories or pages checked:**
  https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/skills/productivity/grilling/SKILL.md;
  https://github.com/mattpocock/skills/blob/49dd158d1076134a641b33efb035946536778336/CHANGELOG.md
  (PR #593, #879, #917 entries). A `grilling/CHANGELOG.md` and the `.changeset/` file were tried
  and returned 404 at that ref (non-blocking).
- **Official docs domains or pages checked:** - none (local-only; no external surface)

---

## Evidence Boundary

> Confirmed from artifacts: word counts (442 / 64 / 169 / 547); STE lint results on base and on
> the spliced draft; no local pin of the step-2 wording; consumer list of `brainstorming`; agent
> role tool sets; upstream grilling text and changelog entry #593 at 49dd158.
> Inferred from patterns: that `Explore` behaves as a read-only grilling role in a blind run; that
> a step 2 handed alone to a subagent is followed as a procedure (A3).
> Not checked: the blind run itself (it is a plan task); whether `sdlc` will move before the PR
> opens; the live round count after merge (A4, accepted risk).
