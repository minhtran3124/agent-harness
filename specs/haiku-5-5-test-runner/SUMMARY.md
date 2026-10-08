# haiku-5-5-test-runner — Summary

Lane: normal
Confidence: high
Reason: changes one agent runtime binding (workflow-engine, warn-mode signal); no block-mode hard gate, reversible by revert.
Flags: workflow-engine
Affects: agents/runtime-bindings.json, scripts/test_render_agent_definitions.py
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> check we can merge or not? need update anything else to adapt with new model family sonnet 5.5 and opus 5.5
>
> yes, fix #247 and open both PRs

The review of PRs #246/#247 found the Claude `test-runner` role was the last binding still on
the 4.x family (`claude-haiku-4-5-20251001`); the user approved a separate PR for it.

## What changed

The Claude `test-runner` role (and its `model_class`) moves from `claude-haiku-4-5-20251001` to
`claude-haiku-5-5`. The renderer test fixture mirrors the binding. No `effort` is added: the
role had none before, and this PR changes only the model.

### Rationale

The coding, reviewer and task-reviewer roles moved to `claude-opus-5-5` in #230 and #244. The
test-runner runs tests and reports results; Haiku 5.5 is the current small model of the same
family, so it keeps the cheap/fast profile while leaving the retired 4.x line.

### Alternatives considered

- `claude-sonnet-5-5`: stronger, but the role is mechanical (run tests, report) and does not need it.
- Add `effort` to the test-runner: deferred; a separate decision from the model swap.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| renderer + entry unit tests | `python3 -m pytest -q scripts/test_render_agent_definitions.py scripts/test_render_runtime_entry.py scripts/test_check_runtime_neutral_sources.py` | 0 | 32 passed | |
| rendered frontmatter | `python3 scripts/render_agent_definitions.py --runtime claude --output-dir /tmp/haiku55-agents-render` | 0 | test-runner `model: claude-haiku-5-5`, no effort | |

The full suite (`scripts/run-tests.sh`) passed locally: ALL GREEN, 638 pytest passed.

### Advisory Findings

- none

### Intent Findings

- none

### Not auto-verified

- Haiku 5.5 runs the test-runner role at least as well as Haiku 4.5 — reached traceability only; no eval run (there is no test-runner eval corpus).
- Deployed `.claude/agents/` keep the old binding until `scripts/deploy-harness.sh` is run.

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
