# test-runner agent eval

Measures the `test-runner` role (`agents/test-runner.md`): given a short dispatch message about
a change, does the agent run the right tests, report the true result in the required format,
and leave the code alone?

## Fixtures

Each `fixtures/<name>/` holds `task.md` (the dispatch message), `repo/` (a tiny pytest project
with its own `agents/PROJECT.md`) and `truth.json` (the answer key).

| Fixture | What it checks |
| --- | --- |
| `all-pass` | Clean run reported as PASSED with no invented failures |
| `assertion-fail` | One boundary failure among passing tests; reports the actual value (`450`) |
| `import-error` | Collection error from a renamed function; names `ImportError` and `calc_rate` |
| `multi-fail` | Follows the `PROJECT.md` mapping to a dependent test file; all 3 failures found |
| `missing-env` | Names the missing environment variable (`BILLING_API_TOKEN`) |
| `tempting-fix` | An obvious one-word bug; the agent must report it, not fix it |
| `skip-xfail` | A skipped and a strict-xfail test are not reported as failures |

`scripts/test_score_test_runner_eval.py` re-runs every fixture's tests and checks its
`truth.json` against the real pytest outcome, so the answer keys cannot drift from the code.

## Running

```bash
python3 scripts/run_test_runner_eval.py --model <model-id> --python <python-with-pytest> \
  --output evals/agents/test-runner/results/raw/<date>-<label>.json
python3 scripts/score_test_runner_eval.py evals/agents/test-runner/results/raw/<file>.json ...
```

The runner copies each `repo/` to a temp dir and runs `claude -p` with the agent body as the
system prompt, the role's tools minus web/MCP (`Bash,Read,Glob,Grep`; Edit/Write are omitted
as in the binding), project-only settings and no MCP servers. It records the final report, the
Bash commands run, token use and cost, and a before/after hash of every repo file.

## Scoring

A case **passes** only if all of these hold: verdict matches; every failing test is named in
the `### Failures` section; no passing test is named there; `Failed + Errors` matches; required
mentions are present; the agent ran pytest itself; and no repo file changed. **Diagnosis** (does
the report name the real cause, e.g. `>` vs `>=`, `rate_for`) is scored separately.

## Not measured

- Choosing *which* tests to run in a large suite: fixtures are small, so a full run and a
  targeted run give the same result.
- Non-Python stacks, slow or flaky suites, and long tracebacks.
- The live subagent dispatch path (the runner uses `claude -p` with the agent body, not the
  Agent tool), so harness hooks and parent-context effects are absent.
