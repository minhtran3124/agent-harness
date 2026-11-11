# Evals for the qa-verifier agent

Each folder is one case, in the layout `claude plugin eval` reads (same as `tests/evals/own/`):
`prompt.md`, `case.yaml`, `graders/` and `files/`. `place-files.sh` also copies `tally.sh` from
`tests/fixtures/qa-verifier/<variant>/`; `run.sh` copies the fixtures next to the cases, and the script looks in both places.

CI does not run these. Runs cost model usage. Results are not committed.

| Case | Checks |
|---|---|
| `fails-on-broken-ac` | The `broken` fixture fails AC2; the report says FAIL with command and exit code; no file is edited |
| `passes-clean-fixture` | The `clean` fixture passes all three ACs; negative or extra rows exist |
| `stays-blind` | A prompt that urges reading `plan.md` is refused; the ACs are still checked |

## Run

From the repo root:

    bash tests/evals/qa-verifier/run.sh --runs 1

If `claude plugin eval` cannot run a plugin subagent in a case, the prompt tells the run to act as the
agent in `plugins/harness/agents/qa-verifier.md`, so the same graders check the agent prompt run as a
`claude -p` style session. Say which way you ran it when you report a result.
