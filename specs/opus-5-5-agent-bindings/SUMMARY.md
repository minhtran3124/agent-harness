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
| full harness suite | `bash scripts/run-tests.sh` | 0 | 584 passed; settings-wiring 1 skipped (.claude/ not built) | |
| rendered frontmatter | `python3 scripts/render_agent_definitions.py --runtime claude --output-dir <tmp>` | 0 | coding opus-5-5/medium, reviewer opus-5/high, task-reviewer opus-5/medium, test-runner haiku/no effort | |
| model-stage distinctness | `python3 scripts/render_runtime_entry.py --runtime claude --model-stage correctness_scorer` | 0 | claude-opus-5-5 (finder: claude-opus-5) | |

### Not auto-verified

- Chosen effort levels improve outcome/cost — reached traceability only; no eval re-run with the new bindings.
- Claude Code honors `effort:` in subagent frontmatter (docs: v2.1.242+) — reached provenance via docs; not exercised in a live dispatch.
- Deployed `.claude/agents/` still carry the old bindings until `scripts/deploy-harness.sh` is run (not run: needs explicit confirmation).

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
