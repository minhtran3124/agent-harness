# Evals for /harness:tickets

Each folder is one case. A run uses `claude -p` in a throwaway directory, with the stub `mocks/gh` first on PATH and a fake `GH_TOKEN`, so it cannot reach GitHub. The fixture stays outside the run's directory, so the run is blind to it. Runs cost model usage, so CI does not run them.

Use `mocks/run_case.sh`, not `claude plugin eval`. That command has no stub, so `prompt.md` grants it no Bash. `mocks/score.py` holds every check.

## Run one case and see the result

From the repo root:

    bash tests/evals/tickets/mocks/run_case.sh secret-in-brief-stops plugins/harness /tmp/eval-out
    python3 tests/evals/tickets/mocks/score.py /tmp/eval-out secret-in-brief-stops
    jq -r '.expectations[] | "\(.passed)  \(.text)"' /tmp/eval-out/grading.json

Results are not committed. They stay in the output folder:

| File | Holds |
|---|---|
| `grading.json` | Each check, pass or fail |
| `final.md` | The report the run gave |
| `questions.md` | Each question for the owner |
| `gh-calls.jsonl` | Each `gh` call, with its stdin |
| `gh-state-after.json` | The fake repo after the run |
| `stream.jsonl` | The full transcript |

`score.py` exits 1 if a `SAFETY` check fails, and stops with `INVALID` if `claude` gave no result. A number from a run describes these fixtures on a stub `gh`, not real use.
