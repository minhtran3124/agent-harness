# eval-runner-hardening — Summary

Lane: normal
Confidence: medium
Reason: no manifest hard gate (scripts/ and evals/ only); 2 flags fired, so normal
Flags: existing behavior, cross-platform
Affects: evals/workflow/intake-classifier, scripts/score_intake_eval.py
Input-type: harness improvement
Route: using-git-worktrees → writing-plans → subagent-driven-development
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/eval-runner-hardening/intent.md @ 4a7fc8ddcdbd6f30a71c5accbd5c1abbeb65ef66

M5 from docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md §6: adopt the playbook's eval-runner hardening (Play 8) for intake-classifier — each fixture pins a `from` commit and `may_change`; run in a scratch worktree with `evals/` removed; scorer copied before the run; stray-file check fails the run; never `--bare`. Intake-classifier has a scorer (scripts/score_intake_eval.py) but no runner yet. Branch from sdlc; PR targets sdlc. Proposed slug: eval-runner-hardening.

### Intake notes

- Confidence is medium: four safe documented defaults are marked `(assumed)` in intent.md
  (headless `claude -p` like the other `scripts/run_*_eval.py` runners; `may_change` covers the
  files intake writes; the existing scorer stays; unit tests never call the real CLI). The user
  approved intent.md with those defaults.
- A plan is required: the change spans more than two files (runner, its tests, fixture metadata,
  README).
- PR base is `sdlc`, not `main`.

## What changed

New `scripts/run_intake_eval.py` runs the intake-classifier eval headless with the playbook's
Play 8 hardening. Each fixture's new `eval.json` pins a `from` commit and a `may_change` list.
The runner checks out a detached scratch worktree at `from`, deletes `evals/`, deploys the
branch-under-test harness into it, runs `claude -p` (never `--bare`), and marks the fixture
`stray` when a file outside `may_change` or any repo ref changes. It scores with a scorer and
answer-key copy made before the first fixture runs. `scripts/test_run_intake_eval.py` covers each
guard with a stub client on throwaway repos, plus one test against the real `runtime/run_state.py`.
The eval README now documents the runner in place of the manual blind-subagent steps.

### Rationale

The approved intent asked for the five Play 8 guards on the cheapest eval first; building one new
runner that follows `run_test_runner_eval.py` reuses its snapshot/integrity code and its headless
`claude -p` precedent, and keeps the existing scorer unchanged as the intent required.

### Alternatives considered

- A fresh clone (or `git archive` export) instead of a linked worktree would hide git history
  and shared refs from the agent, but the intent named a scratch worktree, and reads by absolute
  path stay possible either way; recorded as residual risk instead.
- Keeping the manual blind-subagent run and hardening only setup/checks: rejected because H1
  needs a headless runner and the other runners already use `claude -p`.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| scratch worktree pinned, no evals/ | `python3 -m pytest -q scripts/test_run_intake_eval.py -k scratch` | 0 | 1 passed | SC-1 |
| stray outside may_change fails | `python3 -m pytest -q scripts/test_run_intake_eval.py -k stray` | 0 | 3 passed (incl. real run_state.py writes) | SC-2 |
| scorer copy used | `python3 -m pytest -q scripts/test_run_intake_eval.py -k scorer_copy` | 0 | 1 passed | SC-3 |
| never --bare | `python3 -m pytest -q scripts/test_run_intake_eval.py -k bare` | 0 | 1 passed | SC-4 |
| end to end with stub client | `python3 -m pytest -q scripts/test_run_intake_eval.py -k end_to_end` | 0 | 2 passed | SC-5 |
| fixture metadata valid | `python3 scripts/run_intake_eval.py --check-fixtures` | 0 | 7 lines `ok <fixture>` | SC-6 |
| README documents runner | `grep -q run_intake_eval.py evals/workflow/intake-classifier/README.md` | 0 | | SC-7 |
| all runner tests | `python3 -m pytest -q scripts/test_run_intake_eval.py` | 0 | 13 passed | |

Full suite (intent: "`bash scripts/run-tests.sh` passes"): run 2026-10-16 at `40358a1` →
`1016 passed`, `ALL GREEN`. Cited in prose, not as a row: `rules/plan-format.md` Guardrail 4
forbids whole-suite Verify rows; CI's `tests` job re-runs it.

### Intent Findings

Intent review (blind to PLAN.md) at `40358a1`; no unmet requested outcome.

- gap (record only) — "`bash scripts/run-tests.sh` passes." had no Verify row: recorded above
  in prose (whole-suite rows are forbidden); the suite passes.
- drift, advisory — `may_change` lists a fifth glob, `specs/*/events.jsonl.lock`, beyond the four
  named in the approved (assumed) list. Kept: the clause allows "the files intake legitimately
  writes", and the real `runtime/run_state.py` leaves this file (correctness finding fixed in
  `40358a1`, proven by `test_stray_real_fixtures_allow_every_intake_write`). Nested-path matching
  by `fnmatch` is advisory (see Advisory Findings).
- excess, report-only — the ref check (`ref:` strays), copying the answer keys with the scorer,
  runner CLI options (`--check-fixtures`, `--only`, `--strict`, `--timeout`, `--claude`,
  `--deploy-script`, `--fixtures`), the `run.json` / `<fixture>.raw.txt` record and its statuses,
  and the README residual-risk section. All tighten or document the requested guards; none was
  removed.

### Task-review Minor findings

- Task 1.2 (four README wording gaps: `ref:` strays cannot be allowlisted, `client` may be
  `unknown`, `eval.json` missing from Fixture layout, `--fixtures` undocumented) — fixed in
  `e4a708d`.

### Advisory Findings

Correctness review (six finders, then one independent scorer per location; threshold 75).
Each of these scored 50 and does not block:

- `scripts/run_intake_eval.py:91` — `snapshot()` raises `PermissionError` on a mode-000 file the
  agent leaves, aborting the whole run before `run.json` is written.
- `scripts/run_intake_eval.py:89` — `snapshot()` keeps only regular files, so a new dangling
  symlink, FIFO or directory outside `may_change` is not flagged stray.
- `scripts/run_intake_eval.py:131` — a failed worktree add, deploy (e.g. missing `jq`), request
  read, or undecodable client output raises out of `main`; finished fixtures are lost, deploy
  stderr is hidden, and the existing output dir blocks a re-run.
- `scripts/run_intake_eval.py:142` — the stray check covers only the scratch worktree and refs;
  writes into the main checkout or the shared `.git` config/hooks by absolute path are not seen,
  though the docstring and README say any file change outside `may_change` is caught.
- `scripts/run_intake_eval.py:136` — on timeout only the direct `claude` process is killed; tool
  subprocesses can write after the post-run snapshot or move a ref during the next fixture.
- `scripts/run_intake_eval.py:219` — if `copy_scorer` fails, its temp dir leaks and the created
  output dir blocks the next run.
- `scripts/run_intake_eval.py:105` — the ref check covers the whole shared repo, so another
  session's commit, fetch or stash during a run marks the fixture stray (PLAN Risks accepts this).
- `scripts/run_intake_eval.py:79` — the scorer/answer-key copy sits in a predictable
  `$TMPDIR/intake-eval-scorer-*` dir the same-uid agent could edit; the README claims the copy
  guards against score tampering.
- `scripts/run_intake_eval.py:220` — `--only` still scores all fixtures, so the scorecard shows
  the others as not run.
- `scripts/run_intake_eval.py:163` — the scorer parses only bare `Key: value` lines; a reply that
  formats the header as markdown scores as a miss (a hard-gate miss under `--strict`).
- `scripts/run_intake_eval.py:104` — `fnmatch` `*` matches `/`, so `specs/*/SUMMARY.md` also
  allows deeper paths (documented in the README).

Fixed blocking finding (score 75): `may_change` omitted `specs/*/events.jsonl.lock`, which the
real `runtime/run_state.py` leaves behind, so every correct intake run would be stray — fixed in
`40358a1` with a test that runs the real run-state script.

### Not auto-verified

- No real `claude -p` run was made (it costs money and calls the API). That headless intake
  reaches a classification, that the flags work end to end, and that `may_change` covers every
  real write all reached only traceability (stub client, `claude --help`, one real run-state
  test); a first real run must confirm them.
- Blindness is partial: the agent can still read `truth.md` through the main checkout or
  `git show`, and can write outside the scratch worktree by absolute path (README Residual risk;
  advisory findings above). Not re-run because closing it needs a sandbox, out of scope.

### Rollback

- `git revert <sha>`

### Harness-Delta

- none
