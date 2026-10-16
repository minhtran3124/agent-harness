# gh-308-deletion-test-ceiling — Research Brief

Written 2026-10-16. Pins: repo 03e3555

Depth: **Deep** (intake lane `high-risk`; no upgrade or downgrade on evidence). External surface:
none — no dependency, external system or version-specific API is added or relied on.

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing (adapt one upstream pattern into a local KB entry) |
| **Why this is the lightest credible path** | Every guardrail the trims need already exists locally (qualifier check, reviewer meaning step, shell pins, STE baseline); the only new artifact is a knowledge entry that writes down Pocock's deletion test plus the local condition-word rule, and a two-line pointer in one error message. |
| **Confidence** | 80% — the mechanism is certain; whether each skill yields 60 words without touching a condition sentence is a prediction (A1). |
| **Next step** | `writing-plans`: one task for the reference + audit message, one task per skill trim (3), one bookkeeping task for the backlog rows; each trim task carries the pinned-string list below in its brief. |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Prompt/skill framework with Bash hooks and Python helper scripts |
| Primary language + runtime | Python 3 (system `/usr/bin/python3`, no pytest); Bash |
| Frameworks / platforms | Claude Code skills/hooks; Codex advisory adapter (generated) |
| Relevant packages | pytest via the shared venv `tests/lib.sh` `ensure_pyenv` → `/tmp/harness-tests-venv/bin/python` |
| Detectable versions | none load-bearing |
| Important constraints | `scripts/audit_skill_prompts.py` ceiling 600 words/SKILL.md; `workflow-engine` gate on `skills/*/SKILL.md`; `rules/behavior.md` §1 and §3; STE baseline ratchet `scripts/check_ste_baseline.py` |

---

## Feature Understanding and Assumptions

- **Requested feature:** issue #308 as narrowed by the approved design (D1–D4): a deletion-test
  procedure in a harness-owned KB entry, a pointer to it in the over-ceiling audit message, three
  skill trims to ≤540 words (budget), and two backlog rows marked done.
- **What success appears to mean:** design SC-1…SC-7.
- **Assumptions from the request:** the 600-word ceiling stays; `asd-ste100` stays unmodified.
- **Assumptions still needing confirmation:** A1 (60 words per skill are removable without
  touching a condition sentence) is a prediction; per-skill estimates below.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `scripts/audit_skill_prompts.py` L87–91: the over-ceiling string is `skill exceeds 600-word progressive-disclosure ceiling: skills/<name>/SKILL.md (<n>)`; tests assert the substring `progressive-disclosure ceiling` (`scripts/test_audit_skill_prompts.py` L62, L72, L84, L92), so appending text keeps them green. |
| `Local` | `test_real_repository_matches_expected_surface_shape` pins `totals.skills == 14` and `totals.companion_prompts == 11`. Companion prompts are any `skills/**/*prompt*.md`; a new reference file named with `prompt` would break this test. No committed inventory baseline is checked in CI (`--check-baseline` is used only in `specs/skill-prompt-refactor/`). |
| `Local` | Pinned strings — `finishing-a-development-branch`: `resolve_finish_context.py`, `reports ambiguity, ask the`, `check_review_receipt.py`, `--require correctness,intent --require-audit-if`, `Never merge, force-push`, `Stage named`, `--to ready_to_merge --event pr.opened \|\| true`, `python3 scripts/check_open_questions.py --slug <slug>`, `Open questions closing here`, `python3 scripts/verify_summary.py --sc-history <slug> --base <base>`, `reads committed state only`, `any exit other than 0 or 1` (`tests/scripts/finishing-branch-contract.test.sh`); plus `skills/visual-planner/render_plan.py` (rewritten to `.claude/...` in a consumer, `tests/scripts/consumer-subset.test.sh` L77). |
| `Local` | Pinned strings — `feature-intake`: an `asd-ste100` instruction inside the `- tiny:` … `- normal:` route block (`tests/scripts/context-propagation-regression.test.sh` L226–234, with a mutant check); `python3 .claude/scripts/verify_summary.py` after deploy (`tests/scripts/deploy-worktree-isolation.test.sh` L51–60). |
| `Local` | `session-retro`: no shell test pins it. `scripts/generate_skill_eval_corpus.py` L65–70 names its behaviors: "trace each struggle to an environment lever", "report a clean session without inventing rules", "route approved candidates to the backlog or compound". |
| `Local` | `scripts/check_scope_qualifiers.py` WORDS = if, unless, only, when, never, except, for a new, without; docstring L19 and `test_pilot_step1_split_is_not_listed_known_limit` record the split-scope blind spot. |
| `Local` | `scripts/ste-baseline.json`: `skills/session-retro/SKILL.md` 2, `skills/feature-intake/SKILL.md` 2, `skills/finishing-a-development-branch/SKILL.md` 0, existing references 0. `check_ste_baseline.py` GLOBS include `skills/*/*/*.md`. |
| `Local` | Deploy (`scripts/deploy-harness.sh`) and the Codex adapter (`scripts/render_codex_adapter.py` L253 `_copy_tree(root/"skills"/skill, …)`) copy each skill folder whole; no hard-coded reference-file list found in `adapters/`, `check_codex_packaging.py`, `deploy-harness.sh`, `install-harness.sh`. |
| `Local` | KB: `docs/solutions/README.md` allows `problem_type: bug \| knowledge \| decision`; `knowledge` needs body sections Pattern and How_to_Use; `scripts/rebuild_solution_index.py` rebuilds `INDEX.md` from front-matter fields `problem_type, severity, tags, applicable_when, confirmed_at`. |
| `Local` | `session-retro` has `allowed-tools: Read, …`, so it can read a new `references/` file; the other two already point into `references/`. |
| `Upstream` | Pocock `skills/productivity/writing-for-agents/SKILL.md` @49dd158 L81: "Hunt **no-ops** sentence by sentence … When a sentence fails, delete the whole sentence rather than trim words from it." L39: "Branching is the cleanest disclosure test: inline what every branch needs, and push behind a pointer what only some branches reach." L43 names **sprawl** and prescribes the ladder. |
| `Inference` | Per-skill removable words (prediction): `finishing-a-development-branch` ≈ 65–70 (run-state rationale in Step 3 and in Push and PR → `references/run-state-handoff.md`); `feature-intake` ≈ 45–60 (the "Artifacts scale by signal" list restates `rules/orchestration.md`; the xia2 depth pointer is for xia2, not intake); `session-retro` ≈ 30–60 (overlap between the opening framing and "Then stop", the parenthetical limits in Report). |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:** `scripts/audit_skill_prompts.py` +
  `scripts/test_audit_skill_prompts.py`; the three SKILL.md files; the four shell tests and
  `scripts/generate_skill_eval_corpus.py`; `scripts/check_scope_qualifiers.py` + tests;
  `skills/subagent-driven-development/scripts/review_package.py`; `scripts/check_ste_baseline.py` +
  `scripts/ste-baseline.json`; `docs/solutions/README.md`, `scripts/rebuild_solution_index.py`;
  `docs/harness-experimental/improvement-backlog.md` L24–25.
- **Existing abstractions or extension points:** the problem string list in
  `audit_skill_prompts.py`; each skill's `references/` folder with a `## References` pointer list
  (finishing) or inline pointers (feature-intake); the review package's `## Scope qualifiers` and
  `## STE lint` sections.
- **Conventions worth preserving:** every gate/check states `Verifies:`/`Does not verify:`
  (session-retro's last two lines are that pair and must stay); agent prose follows
  `skills/asd-ste100` (STE-flavored for skills); KB `INDEX.md` is rebuilt, never hand-edited.
- **What can likely be reused:** all review and lint machinery as-is; the existing qualifier
  canaries as SC-5 proof.
- **What appears missing locally:** a written procedure for meeting the ceiling; a
  `references/` folder for `session-retro`.

---

## Upstream Findings

- **Repositories inspected:** `mattpocock/skills` @ `49dd158` (2026-10-09), cloned in an earlier
  research session.
- **Pattern or capability already present upstream:** sentence-level no-op deletion and the
  three-rung disclosure ladder in `writing-for-agents`.
- **Files, modules, or areas worth modeling:** `writing-for-agents/SKILL.md` L39–43 (ladder,
  sprawl) and L80–81 (relevance, no-op hunt).
- **How closely the upstream pattern matches this repo:** close on method; upstream has no
  numeric ceiling and no condition-word rule. The local addition is the condition-word guard,
  which upstream lacks and the local failure record requires.
- **Any upstream gaps or uncertainties:** upstream has no automated check that a deletion kept
  meaning ("There is no automated eval"); this repo supplies that with the qualifier check and
  reviewer.

---

## Docs Findings

No external surface: no official documentation applies.

---

## Recommendation

- **Primary recommendation:** reuse existing machinery; add one KB knowledge entry adapted from
  the upstream pattern; append a pointer to the audit message; trim each skill by whole-sentence
  deletion first, then whole-block disclosure.
- **Why this is the lightest credible path:** no new script or check is needed; the proof
  surface already exists and is tested (`test_pilot_step6_cut_is_listed`).
- **Why the next-best alternative lost:** a new mechanical "deletion-only" checker (diff must
  remove whole sentences) would be a new gate with no recorded failure it alone would catch beyond
  what the qualifier check and reviewer already catch, and it fails the upstream and local
  "observed failure" bar.
- **What would change this recommendation:** if a skill cannot reach 540 words (budget) without a
  condition sentence moving, the plan should stop that skill early (design Error behavior) rather
  than widen scope.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  1. *Scope split on move* (highest). Moving a block out of a step can strand a sentence that
     depended on a leading condition; the qualifier check does not list this (known limit). Mitigation:
     procedure step 4; reviewer meaning check; context-propagation-audit.
  2. *Pinned strings.* Deleting any string in the Evidence Ledger pin rows fails a shell test.
     Mitigation: each trim task's brief lists its pins; grep before delete.
  3. *Self-reference.* `feature-intake` routes every change, including this one. A trim that
     breaks Step 1, 3, 6 or the tiny route breaks intake for every later spec. Mitigation: do not
     touch those steps (design); the context-propagation-regression mutant check covers the tiny
     route.
  4. *Companion-prompt count.* A new `references/*prompt*.md` file breaks
     `test_real_repository_matches_expected_surface_shape`. Mitigation: name new files without
     `prompt`.
  5. *Eval behaviors.* A `session-retro` trim that removes the clean-run stop or the
     backlog/compound routing breaks behaviors the eval corpus scores. Mitigation: keep those
     sentences.
  6. *STE ratchet.* A moved block could raise lint counts; SC-7 guards it.
- **Evidence gaps:** per-skill word yields are predictions; no run of the skill eval corpus is
  planned (out of scope by D2).
- **Version uncertainties:** none.
- **Follow-up questions for the user:** none that change the recommendation.

---

## Source Pack

- **Local files read:** `scripts/audit_skill_prompts.py`, `scripts/test_audit_skill_prompts.py`,
  `skills/session-retro/SKILL.md`, `skills/feature-intake/SKILL.md`,
  `skills/finishing-a-development-branch/SKILL.md`, `tests/scripts/finishing-branch-contract.test.sh`,
  `tests/scripts/context-propagation-regression.test.sh`, `tests/scripts/consumer-subset.test.sh`,
  `tests/scripts/deploy-worktree-isolation.test.sh`, `scripts/generate_skill_eval_corpus.py`,
  `scripts/check_scope_qualifiers.py`, `scripts/test_check_scope_qualifiers.py`,
  `skills/subagent-driven-development/scripts/review_package.py`,
  `skills/subagent-driven-development/task-reviewer-prompt.md`, `scripts/check_ste_baseline.py`,
  `scripts/ste-baseline.json`, `scripts/render_codex_adapter.py`, `docs/solutions/README.md`,
  `scripts/rebuild_solution_index.py`, `docs/solutions/harness/ste-rewrite-drops-scope-qualifiers.md`,
  `docs/harness-experimental/improvement-backlog.md`, `skills/asd-ste100/UPSTREAM.md`,
  `scripts/run-tests.sh`, `tests/lib.sh`.
- **Upstream repositories or pages checked:** https://github.com/mattpocock/skills @ `49dd158`
  `skills/productivity/writing-for-agents/SKILL.md`.
- **Official docs domains or pages checked:** - none (local-only; no external surface)

---

## Evidence Boundary

> Confirmed from artifacts: audit message text and test substrings; companion-prompt count rule;
> every pinned string listed; qualifier word list and Step 1 known limit; STE baseline entries;
> skill-folder-wide copy in deploy and the Codex adapter; KB front-matter and body rules; backlog
> row lines; the 47-test baseline pass in the shared venv.
> Inferred from patterns: per-skill removable word counts; that moving rationale text to
> `references/` does not change agent behavior when the step itself stays.
> Not checked: `context-propagation-regression.test.sh` beyond the tiny-route block (L226–234);
> the skill eval corpus was not run; `scripts/lint-doc-truth.sh` rules for new reference paths were
> not read in full.
