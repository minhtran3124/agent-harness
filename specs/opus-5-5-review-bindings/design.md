# opus-5-5-review-bindings — Design

Status: approved by the user in-session (approach A).

## Purpose

Move the Claude review roles to Claude Opus 5.5 at `medium` effort, following Anthropic's Opus 5.5
migration guidance (Opus 5.5 at `medium` outperforms Opus 5 at `high` on code review, with fewer
tokens). Because the implementer (`coding`) already runs `claude-opus-5-5`, this collapses the
model diversity between implementer, finders, scorer, and intent reviewer. The user explicitly
chose to drop the ensemble-diversity rule rather than move `coding` or use Sonnet 5.5.

## Constraints

- Codex bindings (`gpt-5.6-*`) do not change.
- The `model_stages` map in `adapters/runtime-entry-bindings.json` does not change; stages still
  resolve each review pass to a model through the agent bindings.
- Review independence keeps its remaining guarantees: fresh context per pass, structurally
  read-only reviewer bindings, and plan-blindness for correctness-review and intent-review.
- `.claude/` is redeployed only after explicit user confirmation.

## Approach (A — chosen)

Remove the diversity checks outright for every runtime, and remove every claim that diversity is
enforced or required. Codex's own binding strings stay as they are: `runtime-bindings.json:98`
(`"distinct high-capability review profile"`) is still a true description of the Codex pins
(`gpt-5.6-terra` vs `gpt-5.6-sol`) and is not a claim of enforcement, so it is out of scope.
Rejected: (B) a per-runtime `model_diversity` policy flag — unrequested schema; (C)
downgrading the checks to warnings — a permanent warning on Claude is noise.

## Components

1. **Bindings — `agents/runtime-bindings.json`.** `runtimes.claude.roles.reviewer` and
   `task-reviewer`: `model` → `claude-opus-5-5`, `effort` → `medium`,
   `capabilities.model_class` → `claude-opus-5-5` (drop "distinct from implementation binding").
2. **Validator — `scripts/render_runtime_entry.py`.** Delete the loop that raises
   `correctness scorer must differ from finders` and `intent reviewer must differ from
   implementer`. All other validation (unknown fields, unresolved stages, prompt placeholders,
   missing runtimes) stays.
3. **Dispatch prose.**
   - `skills/correctness-review/correctness-scorer-prompt.md`: replace the "Score with a different
     model than the finders … checked to remain distinct … preserving ensemble diversity" paragraph
     with a model-neutral instruction to resolve the `correctness_scorer` stage; keep the
     `model_stage` / rendered-`model:` resolution sentences and the `render_runtime_entry.py`
     reference.
   - `skills/intent-review/intent-reviewer-prompt.md`: same treatment for "Use a different model
     than the implementer … checked to remain distinct from `implementer`".
   - `agents/reviewer.md` description: remove the sentence about a distinct model class and the
     scorer's ensemble-diversity override; keep the read-only / "not by instruction" claims.
   - `skills/intent-review/SKILL.md:27-28`: drop "preferably with a model different from the
     implementer" from the dispatch sentence; keep "in fresh context" and the quoting rule.
4. **Role contract and inventory.**
   - `agents/agent-contracts.json:33`: reviewer `model_class`
     `review-high-capability-distinct-from-implementer` → `review-high-capability` (same value
     task-reviewer's inventory row already uses). It is a free-form label: `render_agent_definitions.py`
     only prints it, no code compares it.
   - `agents/README.md:12`: reviewer model class "review high-capability, distinct from
     implementer" → "review high-capability".
5. **Tests.**
   - `scripts/test_render_runtime_entry.py`: drop the diversity assertions from the live-binding
     test (rename it accordingly); replace `test_collapsed_model_diversity_is_rejected` with a
     regression test that covers both deleted branches — a binding mapping `correctness_scorer`
     to `reviewer`, and one mapping `intent_reviewer` to `coding`, each now validates;
     golden `claude` `task_reviewer` → `claude-opus-5-5`.
   - `scripts/test_render_agent_definitions.py`: `LEGACY_CLAUDE` reviewer/task-reviewer →
     `claude-opus-5-5` / `medium`; remove `distinct` and `ensemble-diversity` from
     `LOAD_BEARING_SUBSTANCE["reviewer"]["description"]`, together with the comment above them.
   - `tests/scripts/runtime-entry-bindings.test.sh`, `install-harness.test.sh`,
     `deploy-prune.test.sh`: `^model: claude-opus-5$` / `claude-opus-5` → `claude-opus-5-5`.

## Error behavior

A binding where scorer equals finder, or intent reviewer equals implementer, now validates
silently. That is the intended behavior change. No other validator error path changes; an
unresolved role (a stage mapped to a role with no `model`) is still rejected.

Gating: deleting the validator checks trips `weakening-validation`, and editing `agents/`,
`skills/`, and `scripts/` trips `workflow-engine` and the `scripts/` CI warn tier. All are
warn-mode; the lane is already `high-risk`, and the user approved dropping the rule in-session,
so none is an escalation.

## Tests / success criteria

- `python3 scripts/render_runtime_entry.py --root . --check` exits 0 with the new bindings.
- `--model-stage` resolves `task_reviewer`, `intent_reviewer`, `correctness_finder` to
  `claude-opus-5-5` for Claude and is unchanged for Codex.
- Rendered `reviewer.md` / `task-reviewer.md` carry `model: claude-opus-5-5` and `effort: medium`.
- No source outside `specs/`, `evals/`, `docs/`, `.claude/` still claims the diversity rule is
  enforced or required: `grep -rniE 'divers|distinct|different from|must differ'` over the repo
  with those exclusions, with every remaining hit reviewed by hand. Expected survivors are
  unrelated uses (e.g. "Distinct from the other two reviewers", "distinct oracle inputs") and the
  Codex `model_class` string kept above.
- `bash scripts/run-tests.sh` passes.

## Follow-up (after merge and user-confirmed redeploy)

Run the review-chain eval (7 fixtures; `/correctness-review` then `/intent-review` per fixture)
and the task-review eval (7 fixtures) on the new configuration, and compare against
`evals/skills/review-chain/results/2026-07-29-prompt-refactor-ab.md` and
`evals/skills/task-review/results/candidate-v2.json`. Results are recorded as new result files;
existing ones are never overwritten.

## Out of scope

- `docs/solutions/harness/no-report-reviewer-dispatch-is-not-a-pass.md:43,58` mentions ensemble
  diversity as a requirement; it is a dated learning record — flag it for `compound`, don't edit
  here.
