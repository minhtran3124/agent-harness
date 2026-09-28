# opus-5-5-agent-bindings — Summary

Lane: normal
Confidence: high
Reason: changes agent runtime bindings and the renderer (workflow-engine, warn-mode signal); no block-mode hard gate, reversible by revert.
Flags: workflow-engine
Affects: agents/runtime-bindings.json, scripts/render_agent_definitions.py
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> check links
> - https://www.anthropic.com/claude-opus-5-5
> - https://wavect.io/blog/claude-opus-5-5-best-use-cases-workflows/
> - https://explainx.ai/blog/claude-opus-5-5-prompting-guide-2026
> - https://note.com/clear_tern4816/n/n08e1966ef438?hl=en
>
> tìm hiểu và hiểu rõ cách prompt vs opus5.5
> check vs code change của PR hiện tại, xem thử có cần refactor/update gì để match vs opus5.5 hay ko
> review lại các agent cần thiết và update dùng vs opus5.5 + effort phu hop

Scope decisions (user, AskUserQuestion): "coding→5.5 (Recommended)" — coding: claude-opus-5-5 @ medium;
reviewer: claude-opus-5 @ high; task-reviewer: claude-opus-5 @ medium; test-runner unchanged, no effort.
"New branch + worktree (Recommended)".

## What changed

The Claude `coding` role (implementer + correctness scorer) moves from `claude-opus-4-8` to
`claude-opus-5-5`. Claude bindings gain an optional `effort` field: coding `medium`, reviewer
`high`, task-reviewer `medium`, and test-runner none (Haiku). The renderer validates `effort`
against `low|medium|high|xhigh|max`, emits it after `model:`, and rejects it in semantic sources.

### Rationale

Opus 5.5's documented default effort is `medium`, which matches Opus 5 at `high`. It is also
cheaper per token, so the highest-volume role gets it. `render_runtime_entry.py` requires the
implementer/scorer model to differ from finder/intent-reviewer, so the reviewer stays on
`claude-opus-5`. It gets `high` because adversarial bug-hunting is the "difficult root cause"
case the guidance reserves higher effort for.

### Alternatives considered

- reviewer→5.5, coding→opus-5: stronger review, but implementation volume stays on the costlier, weaker model.
- reviewer→sonnet-5: cheapest, with model-family diversity, but a weaker adversarial reviewer.
- effort on test-runner: skipped; effort availability depends on model and Haiku 4.5 was not confirmed.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| renderer + entry unit tests | `python3 -m pytest -q scripts/test_render_agent_definitions.py scripts/test_render_runtime_entry.py scripts/test_check_runtime_neutral_sources.py` | 0 | 31 passed | |
| rendered frontmatter | `python3 scripts/render_agent_definitions.py --runtime claude --output-dir /tmp/opus55-agents-render` | 0 | coding opus-5-5/medium, reviewer opus-5/high, task-reviewer opus-5/medium, test-runner haiku/no effort | |
| model-stage distinctness | `python3 scripts/render_runtime_entry.py --runtime claude --model-stage correctness_scorer` | 0 | claude-opus-5-5 (finder: claude-opus-5) | |

The full suite (`scripts/run-tests.sh`, the CI `tests` job) is cited here in prose rather than
as a Verify row, per `check_verify_rows.py`. After the correctness-review fix it passed locally
(584 pytest passed; settings-wiring 1 skipped because `.claude/` is not built in the worktree).

### Advisory Findings

Correctness-review (6 finders + independent scorer). Only two findings scored at or above 75.
Both were fixed in this SUMMARY: the full-suite Verify row and the `<tmp>` placeholder. The
findings below scored under 75 and are recorded, not fixed:

- `scripts/render_agent_definitions.py:120` (25): the `effort` check keys off presence, so a
  misspelled key, or `effort` on a codex role, is accepted and silently dropped. Roles already
  treat `tools` the same way, and no current binding triggers it. Fix: a closed key set per runtime.
- `scripts/render_agent_definitions.py:17` (25): `CLAUDE_EFFORTS` does not depend on the model.
  `xhigh`/`max` on a Haiku binding would validate, and the runtime may downgrade it silently.
  No current binding triggers it.
- `scripts/render_agent_definitions.py:121` (50): a list or dict `effort` raises `TypeError`,
  which escapes `except ContractError`. It still fails closed, but prints a raw traceback.
- `scripts/check_manifest.py:126`, `scripts/check_runtime_neutral_sources.py:22`,
  `tests/scripts/task-reviewer-readonly.test.sh:12` (0, unmodified-line): these mirrors of
  `FORBIDDEN_SOURCE_FIELDS` did not gain `effort`. Only the renderer rejects `effort:` in
  `agents/*.md`.
- `scripts/test_render_agent_definitions.py:104` (0, unmodified-line): the `model:` assertion
  is an unanchored substring check. `model: claude-opus-5` also matches `claude-opus-5-5`.
- `scripts/render_runtime_entry.py:131` (0, unmodified-line): `--model-stage` returns only the
  model, so stages resolved that way do not carry the effort pin. The pin applies only to
  rendered-frontmatter dispatch.
- `scripts/deploy-harness.sh:499-503` (not scored, unmodified-line; Rule 4, install engine):
  deploy copies the neutral `agents/*.md` into live `.claude/` before rendering. A render
  `ContractError` in between leaves reviewer agents with no `tools:` whitelist.
- Lower-severity unmodified-line notes: the Claude branch of `validate()` does not require
  `model`, so the render raises `KeyError`; `"tools": []` renders an empty `tools:` line;
  `model_class` is hand-mirrored from `model`; `check_manifest.py` splits on `---` without
  anchoring to a line.

### Intent Findings

- gap (advisory): the link research and the "no refactor needed for the
  `feat/cheap-adoptions-spotify-report` PR" verdict were given only in conversation. The
  sources are recorded here: the effort defaults come from anthropic.com/claude-opus-5-5 and
  wavect.io ("start at medium"; raise effort only when the first attempt's miss can be named).
  The prompting anti-patterns come from explainx.ai and note.com. Of the PR's changed skill and
  rule lines, none contained them.
- excess (report-only): `CLAUDE_EFFORTS` admits `xhigh`/`max`, which no role uses, and
  `effort` joined `FORBIDDEN_SOURCE_FIELDS`. Both follow the existing Codex/source-neutrality
  shape.

### Not auto-verified

- Chosen effort levels improve outcome/cost — reached traceability only; no eval re-run with the new bindings.
- Claude Code honors `effort:` in subagent frontmatter (docs: v2.1.242+) — reached provenance via docs; not exercised in a live dispatch.
- Deployed `.claude/agents/` still carry the old bindings until `scripts/deploy-harness.sh` is run (not run: needs explicit confirmation).

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
