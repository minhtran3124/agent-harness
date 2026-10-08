# haiku-5-5-test-runner — Summary

Lane: normal
Confidence: high
Reason: changes one agent runtime binding (workflow-engine, warn-mode signal); no block-mode hard gate, reversible by revert.
Flags: workflow-engine
Affects: agents/runtime-bindings.json, scripts/test_render_agent_definitions.py, scripts/run_test_runner_eval.py, scripts/score_test_runner_eval.py, scripts/test_score_test_runner_eval.py, scripts/run-tests.sh, evals/agents/test-runner/
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> check we can merge or not? need update anything else to adapt with new model family sonnet 5.5 and opus 5.5
>
> yes, fix #247 and open both PRs

> run eval for haiku 5.5 to measure

The review of PRs #246/#247 found the Claude `test-runner` role was the last binding still on
the 4.x family (`claude-haiku-4-5-20251001`); the user approved a separate PR for it, then asked
for an eval to measure the change.

## What changed

The Claude `test-runner` role (and its `model_class`) moves from `claude-haiku-4-5-20251001` to
`claude-haiku-5-5`. The renderer test fixture mirrors the binding. No `effort` is added: the
role had none before, and this PR changes only the model.

New eval `evals/agents/test-runner/`: 7 pytest fixtures with answer keys, a runner
(`scripts/run_test_runner_eval.py`) that drives the real agent body through `claude -p`, and a
deterministic scorer (`scripts/score_test_runner_eval.py`). Its tests re-derive every answer
key from a real pytest run and are wired into `scripts/run-tests.sh`.

Results (n = 3, `evals/agents/test-runner/results/2026-10-08-haiku-4-5-vs-5-5.md`): Haiku 5.5
passed 21/21 cases, Haiku 4.5 20/21 (one double-counted failure total). Median time per case
~9.5 s vs ~20 s; CLI-reported cost ~$0.011 vs ~$0.15 per 7-case run.

### Rationale

The coding, reviewer and task-reviewer roles moved to `claude-opus-5-5` in #230 and #244. The
test-runner runs tests and reports results; Haiku 5.5 is the current small model of the same
family, so it keeps the cheap/fast profile while leaving the retired 4.x line.

### Alternatives considered

- `claude-sonnet-5-5`: stronger, but the role is mechanical (run tests, report) and does not need it.
- Add `effort` to the test-runner: deferred; a separate decision from the model swap.

### Deviations

- The scorer was fixed after the first scoring (emoji in the verdict heading; a passing test named
  on a "passed" line inside `### Failures`). Both bugs were found by reading every failed case,
  both have tests, and the results file discloses the before/after numbers.

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| renderer + entry unit tests | `python3 -m pytest -q scripts/test_render_agent_definitions.py scripts/test_render_runtime_entry.py scripts/test_check_runtime_neutral_sources.py` | 0 | 32 passed | |
| eval scorer + answer-key provenance tests | `python3 -m pytest -q scripts/test_score_test_runner_eval.py` | 0 | 26 passed | |
| re-score the recorded A/B runs | `python3 scripts/score_test_runner_eval.py evals/agents/test-runner/results/raw/2026-10-08-haiku-5-5-run1.json` | 0 | 7/7 | |
| rendered frontmatter | `python3 scripts/render_agent_definitions.py --runtime claude --output-dir /tmp/haiku55-agents-render` | 0 | test-runner `model: claude-haiku-5-5`, no effort | |

The full suite (`scripts/run-tests.sh`) passed locally: ALL GREEN, 638 pytest passed.

### Advisory Findings

- none

### Intent Findings

- none

### Not auto-verified

- Haiku 5.5 runs the test-runner role at least as well as Haiku 4.5 — reached truth on 7 small Python fixtures (n = 3); not measured for test selection in large suites, other stacks, or live subagent dispatch.
- The cost ratio — reached provenance only via the CLI's `total_cost_usd`; model prices were not checked independently.
- Deployed `.claude/agents/` keep the old binding until `scripts/deploy-harness.sh` is run.

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
