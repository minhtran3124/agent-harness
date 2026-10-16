# Intent: Eval-runner hardening for intake-classifier

Author: Minh Tran
Status: approved

## Problem

The intake-classifier eval has a deterministic scorer (`scripts/score_intake_eval.py`) but no
runner. Runs are started by hand with blind subagents, in the live checkout. Nothing pins the
repo state a run starts from, nothing stops the agent under test from reading `truth.md` or
editing the scorer, and nothing detects files the run should not have touched. So a run result
cannot be trusted or reproduced, and H1 (a continuous eval gate on config changes) has no sound
runner to build on.

## Proposed outcome

A runner for the intake-classifier eval that applies the playbook's Play 8 hardening:

- each fixture pins a `from` commit and a `may_change` list;
- each run happens in a scratch worktree at that commit, with `evals/` removed;
- the scorer is copied out before the run, and the copy does the scoring;
- a file changed outside `may_change` fails the run;
- the agent under test runs with the harness config loaded — never `--bare`.

## Affected users and systems

Harness maintainers who run evals; `scripts/` (new runner, its tests) and
`evals/workflow/intake-classifier/` (fixture metadata, README). Later consumer: H1.

## Constraints

- Start the agent headless with `claude -p`, as the other `scripts/run_*_eval.py` runners do
  (assumed).
- `may_change` for intake allows the files intake legitimately writes:
  `specs/<slug>/SUMMARY.md`, `intent.md`, `RUN.json`, `events.jsonl` (assumed).
- Keep the existing scorer and its result format; the runner feeds it, it does not replace it
  (assumed).
- The unit tests must not call the real `claude` CLI or the API (assumed).
- Works on Linux and macOS (no `timeout`, no GNU-only flags).

## Out of scope

- Hardening the other four eval runners (review-chain, review-prompt, task-review, test-runner).
- Any CI or merge gate on eval results (that is H1).
- Changing `skills/feature-intake/` or the fixtures' answer keys.

## Open questions

none

## What success looks like

- A unit test shows the agent's worktree has no `evals/` directory and starts at the pinned
  `from` commit.
- A unit test shows a run that changes a file outside `may_change` is marked failed.
- A unit test shows the runner scores with a scorer copy made before the run, so an edit to the
  in-tree scorer during the run does not change the result.
- A unit test shows the runner never passes `--bare` to the client.
- `bash scripts/run-tests.sh` passes.

## Original request

M5 from docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md §6: adopt the playbook's eval-runner hardening (Play 8) for intake-classifier — each fixture pins a `from` commit and `may_change`; run in a scratch worktree with `evals/` removed; scorer copied before the run; stray-file check fails the run; never `--bare`. Intake-classifier has a scorer (scripts/score_intake_eval.py) but no runner yet. Branch from sdlc; PR targets sdlc. Proposed slug: eval-runner-hardening.

User reply: "go ahead"
