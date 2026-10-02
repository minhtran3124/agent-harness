# opus-5-5-review-bindings — Research Brief

Depth: **Deep** (intake lane `high-risk`; no upgrade needed). External surface: yes — the change
relies on version-specific model IDs and the effort parameter (`claude-opus-5-5`, `effort: medium`).

## Bottom Line

| Field | Value |
|---|---|
| **Recommendation** | reuse existing — edit the binding JSON, delete one validator loop, reword prose/contracts, update golden tests |
| **Why this is the lightest credible path** | Every model choice already flows from `agents/runtime-bindings.json` through `render_agent_definitions.py` / `render_runtime_entry.py`; no new mechanism is needed |
| **Confidence** | 90% |
| **Next step** | `writing-plans` with the file set in `design.md` §Components |

## Repo Snapshot

| Field | Detected |
|---|---|
| Repo type | Claude Code skill framework / workflow harness (meta-repo) |
| Primary language + runtime | Markdown prompts; Python 3 scripts; Bash hooks/tests |
| Frameworks / platforms | Claude Code (agent frontmatter `model:` / `effort:` / `tools:`); Codex advisory alpha |
| Relevant packages | none (no dependency change) |
| Detectable versions | Claude Code 2.1.x per eval result files; Codex CLI 0.147.0 (CLAUDE.md) |
| Important constraints | `.claude/` redeploy needs user confirmation; `scripts/run-tests.sh` before touching `scripts/`; `workflow-engine` + `weakening-validation` are warn-mode gates |

## Feature Understanding and Assumptions

- **Requested feature:** reviewer and task-reviewer on `claude-opus-5-5` at `medium`; drop the ensemble-diversity rule; then run the review-chain and task-review evals.
- **What success appears to mean:** rendered agents carry the new model/effort; validator, prose, contracts and tests no longer require or claim model diversity; full suite green; eval results recorded.
- **Assumptions from the request:** Codex unchanged; stage map unchanged.
- **Assumptions still needing confirmation:** none.

## Evidence Ledger

| Label | Evidence |
|---|---|
| `Local` | `agents/runtime-bindings.json:22-49` pins reviewer `claude-opus-5`/`high`, task-reviewer `claude-opus-5`/`medium`; coding `claude-opus-5-5`/`medium` |
| `Local` | `scripts/render_runtime_entry.py:99-107` raises on scorer==finder and intent_reviewer==implementer; `adapters/runtime-entry-bindings.json` maps scorer→coding, finder/intent→reviewer |
| `Local` | `scripts/render_agent_definitions.py:227` only prints `model_class`; no code compares it |
| `Local` | Diversity prose: `correctness-scorer-prompt.md:27-29`, `intent-reviewer-prompt.md:23-25`, `intent-review/SKILL.md:27-28`, `agents/reviewer.md:3`, `agents/agent-contracts.json:33`, `agents/README.md:12` |
| `Local` | Golden pins: `test_render_runtime_entry.py:25-33,50,80-87`, `test_render_agent_definitions.py:14-26,51-53`, `runtime-entry-bindings.test.sh:37`, `install-harness.test.sh:56`, `deploy-prune.test.sh:32` |
| `Local` | Prior eval runs did not use production bindings: review-chain 2026-07-22 and 2026-07-29 used one blind `sonnet` reviewer (`--effort low` in 07-29); task-review `candidate-v2.json` ran `claude-fable-5`, reasoning `standard` |
| `Local` | `scripts/run_task_review_eval.py` is an automated runner taking `--mode`, `--model`, `--reasoning`, `--output`; review-chain is a manual protocol (README) |
| `Local` | `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md` credits the caught defect to "a different reading frame" (an independent/external reviewer), and names ensemble diversity as a chain requirement |
| `Docs` | claude-api skill `shared/model-migration.md` (Opus 5.5 section): effort is the primary thinking control, default `medium`; Opus 5.5 at `medium` outperforms Opus 5 at `high` on coding and code-review evals with fewer tokens; set effort explicitly |
| `Inference` | Removing model diversity removes one source of reviewer independence; fresh context, read-only bindings and plan-blindness remain |

## Local Findings

- **Relevant files:** listed in the Evidence Ledger and `design.md` §Components.
- **Existing extension points:** `agents/runtime-bindings.json` (per-runtime role pins) → `scripts/render_agent_definitions.py` (renders `.claude/agents/*.md`) and `scripts/render_runtime_entry.py` (stage→model resolution).
- **Conventions worth preserving:** semantic prompts carry no vendor model labels (`scripts/check_runtime_neutral_sources.py` enforces it) — reworded prose must stay model-neutral; `LOAD_BEARING_SUBSTANCE` tokens in `test_render_agent_definitions.py` protect claims that must survive rewording.
- **What can be reused:** the whole render/validate pipeline; only data and one loop change.
- **What appears missing:** nothing required.

## Upstream Findings

- **Repositories inspected:** none applicable — this is a local policy change in a self-authored harness; the related upstream (obra/superpowers, the fork origin) has no model-binding layer.
- **Pattern upstream:** none found.
- **Gaps:** none.

## Docs Findings

- **Official sources checked:** Anthropic model-migration guide bundled with the claude-api skill (Opus 5.5 and Sonnet 5.5 sections), read earlier this session.
- **Version-matched status:** matches the target model `claude-opus-5-5`.
- **Built-in capabilities:** Claude Code agent frontmatter already accepts `model:` and `effort:` (the `coding` role renders `effort: medium` today).
- **Recommended workflow:** set effort explicitly per role; lower effort instead of prompting "think less"; re-test with evals.
- **Caveats:** guidance's quality claim is Anthropic's measurement, not this repo's — the follow-up eval is the local check.

## Recommendation

- **Primary recommendation:** reuse existing pipeline (approach A in `design.md`).
- **Why lightest:** data edit + loop deletion + prose/tests; no schema or new code path.
- **Why next-best lost:** a per-runtime `model_diversity` flag (B) adds unrequested schema; warn-only (C) creates permanent noise on Claude.
- **What would change it:** the eval showing a regression in catch rate or false positives on the new config.

## Risks, Unknowns, and Follow-Up Questions

- **Technical risks:**
  - Scorer and finders now share one model, so the scorer may re-confirm a finder's shared blind spot (the reason the rule existed). Mitigation remains the plan-blind, fresh-context scorer and the threshold-75 filter.
  - Intent-review and implementer share a model; drift the implementer cannot see may also be invisible to the intent reviewer.
  - `.claude/` keeps the old pins until a user-confirmed redeploy; evals must run after it, or they measure the old config.
- **Evidence gaps:** prior eval baselines used `sonnet` / `claude-fable-5`, not the production `claude-opus-5` binding — a new run on `claude-opus-5-5` compares across both model and configuration, so a difference cannot be attributed to the binding change alone.
- **Version uncertainties:** none for the IDs; effort level semantics per Anthropic's guide.
- **Follow-up questions:** none blocking.

## Source Pack

- **Local files read:** `agents/runtime-bindings.json`, `agents/agent-contracts.json`, `agents/README.md`, `agents/reviewer.md`, `adapters/runtime-entry-bindings.json`, `scripts/render_runtime_entry.py`, `scripts/render_agent_definitions.py`, `scripts/test_render_runtime_entry.py`, `scripts/test_render_agent_definitions.py`, `tests/scripts/runtime-entry-bindings.test.sh`, `tests/scripts/install-harness.test.sh`, `tests/scripts/deploy-prune.test.sh`, `skills/correctness-review/correctness-scorer-prompt.md`, `skills/intent-review/intent-reviewer-prompt.md`, `skills/intent-review/SKILL.md`, `evals/skills/review-chain/README.md`, `evals/skills/review-chain/results/2026-07-22-threshold-75.md`, `evals/skills/review-chain/results/2026-07-29-prompt-refactor-ab.md`, `evals/skills/task-review/README.md`, `evals/skills/task-review/results/candidate-v2.json`, `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md`
- **Upstream repositories or pages checked:** - none found
- **Official docs domains or pages checked:** claude-api skill `shared/model-migration.md` (Opus 5.5 and Sonnet 5.5 sections)

## Evidence Boundary

> Confirmed from artifacts: every pin, check, prose location and golden test above; the eval runners' interfaces and prior eval models.
> Inferred from patterns: the independence cost of collapsing model diversity.
> Not checked: whether Opus 5.5 at `medium` performs better on this repo's fixtures — that is what the follow-up eval measures.
