# review-policy — Research Brief

Written 2026-10-11. Pins: repo 33d6ed4 + uncommitted

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing: register the policy in `scripts/render_skill_prompt.py` `CONTEXT_MATRIX` instead of writing a new Read-line test; rewrite the wording in place against the pinned-string inventory below |
| **Why this is the lightest credible path** | The matrix already proves which child context must Read which rule (`context-propagation-regression.test.sh`, `scripts/test_render_skill_prompt.py`), so the new delivery is enforced by the same mechanism as `rules/auto-correct-scope.md` |
| **Confidence** | 80% |
| **Next step** | `writing-plans`: three waves per design D1, with the matrix entries and the checker update in wave 3 |

---

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Prompt/skill framework (Markdown skills, Bash hooks, Python scripts) |
| Primary language + runtime | Markdown prompts; Python 3 and Bash for checks |
| Frameworks / platforms | Claude Code (primary), Codex advisory alpha adapter |
| Relevant packages | none (no dependency change) |
| Detectable versions | not load-bearing; no external surface |
| Important constraints | `audit_skill_prompts.py` 600-word SKILL ceiling; `check_runtime_neutral_sources.py` zero-tolerance; `lint-doc-truth.sh`; workflow-engine gate requires the context-propagation audit |

---

## Feature Understanding and Assumptions

- **Requested feature:** one review policy (`rules/review-policy.md`) read by the review prompts, and a plain-wording rewrite of every review agent and skill (design `specs/review-policy/design.md`, D1–D8).
- **What success appears to mean:** the design's Success criteria; the suite green after every wave; the in-scope total at most 7,867 words (budget).
- **Assumptions from the request:** wording changes keep each reviewer's oracle, inputs, output schema (apart from `checked_against`), categories, and blocking rules.
- **Assumptions still needing confirmation:** none that change the recommendation; the Codex gap below is an accepted, pre-existing limit.

---

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `scripts/render_skill_prompt.py:13-67` `CONTEXT_MATRIX` maps each context to its required rule reads. `task-reviewer` and `correctness-scorer` have empty `required` with a rationale; there is no `intent-reviewer` entry, only `intent-controller`. |
| `Local` | `scripts/test_render_skill_prompt.py:43-56` asserts the matrix key set, so a new `intent-reviewer` key must update that test; `:65` mutates each required token to prove it is load-bearing. |
| `Local` | Pinned strings are mostly line-based `grep -q`/`-qF`: a pinned phrase must stay on one physical line (inventory in Local Findings). |
| `Local` | `tests/scripts/scorer-threshold-contract.test.sh:29` scans all of `skills/` for threshold phrasings (`threshold N`, `scoring N or`, `score >= N`, `default **N**`), and every N must equal 75 (measured 2026-10-11 `review-config.json`). |
| `Local` | `tests/scripts/rule-loading-tiers.test.sh:29,33` and `CLAUDE.md:7` enumerate the four path-scoped rules; nothing else lists them (searched `README.md`, `HARNESS.md`, `agents/README.md`, `skills/README.md` for `path-scoped`, `four path`, and rule filenames). |
| `Local` | `agents/*.md` are hand-written sources; `render_agent_definitions.py` copies the body byte-for-byte (`test_render_agent_definitions.py:100`) and Codex receives the same body; descriptions must stay one line. |
| `Local` | Codex ships no `rules/` (no `rules` match in `render_codex_adapter.py`, `deploy-codex-adapter.sh`, `install-codex-harness.sh`, `adapters/codex/project/harness-instructions.md`), so an explicit Read of a rule does not resolve there; the existing `auto-correct-scope.md` Read has the same gap. |
| `Local` | The workflow-engine pattern does not match `prompts/shared.md`, `prompts/angles/*.md`, or `references/review-chain.md` (`tests/scripts/workflow-engine-regex-parity.test.sh:15`); the `*-prompt.md` files and `rules/review-policy.md` do match, so this change still triggers the audit. |
| `Local` | `skills/subagent-driven-development/SKILL.md` is at 600 words (measured 2026-10-11 `audit_skill_prompts.py`), so no wording may be added there. |
| `Local` | Fifteen near-verbatim repeats across the in-scope files, for example the `model_stage` paragraph (`task-reviewer-prompt.md:5-8` = scorer `:29-32` = intent prompt `:25-28`) and the `REVIEW_PACKAGE_PATH` paragraph (`shared.md:15-19` ≈ intent prompt `:60-63`). |
| `Upstream` | Anthropic Code Review injects `REVIEW.md` into every agent in the review pipeline and uses it for always-flag and skip lists, such as skipping generated code (code.claude.com/docs/en/code-review; support.claude.com article 14233555). |
| `Upstream` | The SDLC playbook Play 9 caps nits at 5 (`docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md:146`); design D4 deliberately keeps no cap. |
| `Upstream` | Anthropic prompting guidance favours clear, explicit instructions, and the "colleague with minimal context" test (platform.claude.com prompting best practices); a secondary report on Opus 5.5 guidance says to drop "think carefully" lines (searchenginejournal.com). |
| `Inference` | Most of the 7,867-word budget can be met by deduping the repeats above, since each copy lives in a fresh context only where the prompt is self-contained; a repeat may stay where a child prompt needs it, because child prompts do not inherit the controller's text. |

---

## Local Findings

- **Relevant files, modules, scripts, docs, tests:**
  - **Pinned strings to keep, each on one line:**
    - `intent-review/SKILL.md`: `verbatim primary oracle`, `ask the user instead of reconstructing`, ``never `PLAN.md` prose``, `**gap:**`, `**drift:**`, `**excess:**`, `REVIEW_PACKAGE_PATH`, `rules/auto-correct-scope.md`.
    - `intent-reviewer-prompt.md`:
      - a line matching `must .*read.*PLAN.md` or `do not read.*PLAN.md`;
      - `FORBIDDEN from reading.*PLAN.md` on one line;
      - `REVIEW_PACKAGE_PATH`, `do not rebuild the same full diff`, `model_stage: intent_reviewer`.
    - `review-chain.md`: `branch review package`, `oracle inputs and blindness rules remain unchanged`; it must not contain `spec-reviewer-prompt.md` or `code-quality-reviewer-prompt.md`.
    - `correctness-review/SKILL.md`: `REVIEW_PACKAGE_PATH`, `rules/auto-correct-scope.md`.
    - `prompts/shared.md`:
      - `REVIEW_PACKAGE_PATH`, `do not rebuild the same full diff`;
      - a `**Read .*auto-correct-scope.md` line;
      - the range from `Rule 4 STOP cases:` to `This list is a summary`, holding `schema`, `API contract`, `remov`, `external`, `auth`, `session`, `high-blast`, `replac`;
      - no `{{` or `}}`.
    - `correctness-reviewer-prompt.md`: the six backticked angle names.
    - `correctness-scorer-prompt.md`:
      - the `"score": <…>` line with at least three anchors;
      - `**0**`/`**25**`/`**50**`/`**75**`/`**100**`;
      - `default threshold is **75**`, `floor is 60`;
      - `model_stage: correctness_scorer`.
    - `task-reviewer-prompt.md`:
      - `spec_verdict: pass | fail | cannot_verify`, `quality_verdict: approved | needs_fixes`, `Critical | Important | Minor`;
      - `IMPLEMENTER_REPORT_PATH`, `REVIEW_PACKAGE_PATH`, `Fix round`;
      - `Spec verdict also covers scope`, `**Files:**`, `Ignore bookkeeping paths`;
      - `model_stage: task_reviewer`.
    - `agents/reviewer.md`: `structurally read-only`, `not by instruction`, `Acknowledged limitation`, `never fix`, `structural, not a promise`.
    - `agents/task-reviewer.md`: `cannot write, edit, spawn agents`; no `tools`, `model`, `effort`, or `memory` frontmatter.
    - The harness-only paths (`scripts/render_runtime_entry.py`, `scripts/harness-status.sh`) must keep a "harness repo" marker within one line for `lint-doc-truth.sh`.
  - **Soft pin:** `scripts/score_task_review_eval.py:29-34` parses `spec_verdict`, `needs_fixes`, `plan-mandated`, `cannot_verify` from task-reviewer output.
- **Existing abstractions or extension points:**
  - `CONTEXT_MATRIX` (`required`, `required_reads`, `rationale`);
  - `render_skill_prompt.py` composition of `shared.md` with each angle;
  - `check_task_review_contract.py` `REQUIRED` tuple.
- **Conventions worth preserving:**
  - rules use block-list `paths:` frontmatter;
  - rule and skill text is runtime-neutral: no `.claude/rules/`, no slash invocations, no vendor model labels;
  - inline policy copies are guarded by drift tests.
- **What can likely be reused:**
  - `CONTEXT_MATRIX` for delivery proof;
  - `check_task_review_contract.py` for `checked_against`;
  - `rule-loading-tiers.test.sh` for the inventory.
- **What appears missing locally:**
  - an `intent-reviewer` context entry in the matrix;
  - any check that the task reviewer reads a rule.

---

## Upstream Findings

- **Repositories inspected:** none cloned; Anthropic Code Review documentation and the SDLC playbook course (via the 2026-10-10 research note).
- **Pattern or capability already present upstream:** one repo-level `REVIEW.md` injected into every review agent, holding severity guidance and always-flag and skip lists.
- **Files, modules, or areas worth modeling:** the skip list (generated code) and the Nit/Important split.
- **How closely the upstream pattern matches this repo:** close in content. Delivery differs: upstream injects the file into every agent, while here a path-scoped rule plus an explicit Read reaches only the contexts that need it.
- **Any upstream gaps or uncertainties:** the exact severity syntax upstream was not found; Opus 5.5 prompting specifics come from one secondary source.

---

## Docs Findings

No external surface: no dependency, integration, or version-specific API changes. The upstream pages above inform the wording standard only.

---

## Recommendation

- **Primary recommendation:** reuse existing.
  - **Delivery:**
    - add `rules/review-policy.md` to `required` and `required_reads` of `task-reviewer` and `correctness-reviewer`;
    - add an `intent-reviewer` entry for `skills/intent-review/intent-reviewer-prompt.md`;
    - update `scripts/test_render_skill_prompt.py`'s key set;
    - keep `correctness-scorer` empty with its rationale.
  - **Checker:** add `checked_against` to the `check_task_review_contract.py` `REQUIRED` tuple.
  - **Rewrite:** reword against the pinned-string inventory, keeping each pin on one line.
- **Why this is the lightest credible path:** the matrix is already the canonical delivery proof and is mutation-tested; a separate grep test would duplicate it and could drift from it.
- **Why the next-best alternative lost:** a standalone Read-line test (the design's first sketch) duplicates the matrix and is not covered by `context-propagation-regression.test.sh`.
- **What would change this recommendation:** a reason that the matrix cannot hold an `intent-reviewer` key, for example another test that enumerates contexts by name.

---

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - re-wrapping a sentence breaks a line-based pin even when the words are unchanged;
  - writing any threshold phrasing with a number other than 75 anywhere under `skills/` fails the threshold contract;
  - adding words to `subagent-driven-development/SKILL.md` breaks the 600-word ceiling;
  - removing a repeat from a child prompt can drop an instruction that the child context does not receive otherwise; the meaning-equivalence review must check this per file.
- **Evidence gaps:**
  - whether a fresh reviewer actually follows the new Read (design A1) is proven only at traceability tier by the matrix, plus the audit;
  - Codex contexts cannot resolve rule Reads at all.
- **Version uncertainties:** none.
- **Follow-up questions for the user:** none.
- **Recorded, not acted on:** stale counts outside scope:
  - `scripts/ci-strict-gate.sh:76` says "all 8 files";
  - `docs/research/2026-09-09-spotify-portal-ai-plugins.md` says "four of nine".

---

## Source Pack

- **Local files read:**
  - `specs/review-policy/design.md`, `specs/review-policy/intent.md`;
  - `scripts/render_skill_prompt.py`, `scripts/run_review_chain_eval.py`, `scripts/check_task_review_contract.py`;
  - `tests/scripts/rule-loading-tiers.test.sh`;
  - `skills/correctness-review/prompts/shared.md`, `skills/intent-review/intent-reviewer-prompt.md`, `skills/subagent-driven-development/task-reviewer-prompt.md`;
  - `docs/solutions/harness/review-model-diversity-dropped-decisions.md`, `docs/solutions/harness/plan-anchored-task-review-misses-fixture-fitted-bugs.md`;
  - `docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md`, `specs/opus-5-5-prompt-audit/design.md`, `evals/skills/review-chain/README.md`;
  - plus a delegated read-only sweep of all 16 in-scope files, `tests/`, `scripts/`, `evals/`, deploy and Codex scripts (findings cited above with file:line).
- **Upstream repositories or pages checked:**
  - https://code.claude.com/docs/en/code-review
  - https://support.claude.com/en/articles/14233555-set-up-code-review-for-claude-code
  - https://academy.claude.com/courses/ai-native-sdlc-playbook/ai-in-the-pr-review-loop
  - https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
  - https://www.searchenginejournal.com/anthropic-claude-opus-5-5-prompting-guidance/591278/
- **Official docs domains or pages checked:** - none (local-only; no external surface)

---

## Evidence Boundary

> **Confirmed from artifacts:**
> - the `CONTEXT_MATRIX` contents;
> - the rule-inventory locations;
> - the 7,867-word total (measured 2026-10-11 `wc -w`);
> - the scripted benchmark's hardcoded prompt;
> - the agents being hand-written sources;
> - the pinned-string inventory: delegated sweep, with the matrix re-read directly.
>
> **Inferred from patterns:**
> - that the 7,867-word budget is reachable by deduping;
> - that a fresh reviewer follows an explicit Read.
>
> **Not checked:**
> - a live run of any rewritten prompt;
> - an official Anthropic Opus 5.5 prompting page;
> - the Codex runtime behavior of rule Reads.
