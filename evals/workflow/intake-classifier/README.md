# Intake-Classifier Eval (auto-score / hardened runner)

Measures whether **`/feature-intake`** assigns the correct **lane · confidence · hard-gate** for
a request. Sibling of `../../skills/review-chain` — same honesty model, different oracle: this scores the
*router* the whole workflow hinges on. The scorer is automatic (`scripts/score_intake_eval.py`,
unit-tested); the classification runs come from the hardened runner `scripts/run_intake_eval.py`
(see Running).

## Claim discipline (read first)

This benchmark measures **only** whether `/feature-intake` classifies **these fixtures** correctly.
It is *not* evidence about other skills, the full workflow chain, or real-world classification
accuracy. A number here is a claim about *this fixture set and this skill*, nothing more — state
that scope wherever it is cited (`not_observed != absent` — a request shape we did not seed is
unmeasured, not "handled").

The single non-negotiable metric is **hard-gate respect**: a fixture whose truth declares a hard
gate (auth · authorization · data-loss/migration · audit · external provider · public contract ·
high-blast file) MUST be classified `high-risk`. A downgrade there is a safety failure, not a
scoring miss — `score_intake_eval.py --strict` exits non-zero on it.

## Fixture layout

Each fixture is `fixtures/<name>/` with:

- **`request.md`** — the user request to classify (what a blind runner sees).
- **`truth.md`** — a parseable header + prose rationale. Header keys the scorer reads:

  | Key | Meaning |
  |---|---|
  | `expected_lane` | `tiny` / `normal` / `high-risk`, or `any` (lane not asserted — e.g. an ambiguity fixture) |
  | `expected_confidence` | `high` / `medium` / `low` |
  | `expected_hard_gate` | the hard-gate class, or `none` |
  | `expected_flags_include` | flags that MUST appear (comma-sep), or `none` |
  | `expected_escalate` | `yes` / `no` |
  | `must_not_downgrade` | `true` for hard-gate fixtures |
- **`eval.json`** — the pinned `from` commit and the `may_change` globs the runner reads (see
  `### eval.json` below). The runner refuses a fixture without it.

## Running (hardened runner)

`scripts/run_intake_eval.py` runs the classifier once per fixture, headless, and scores the run.
Run it from the repo root of the branch under test:

```
python3 scripts/run_intake_eval.py --model <model> --output-dir evals/workflow/intake-classifier/results/<run>
```

Options: `--fixtures <dir>` reads another fixture set (default
`evals/workflow/intake-classifier/fixtures`); `--only <fixture>` runs one fixture; `--strict` passes `--strict` to the scorer;
`--timeout <s>` is the per-fixture limit (default 600); `--claude <path>` and
`--deploy-script <path>` replace the client and `scripts/deploy-harness.sh`. The runner refuses
an existing `--output-dir`. Check the fixture metadata without running anything:
`python3 scripts/run_intake_eval.py --check-fixtures`.

**Prerequisites:** the `claude` CLI on `PATH` (or `--claude`), `git`, and `jq` (the deploy script
needs it).

Then record the scorecard in `results/<date>-<label>.md` (from `results/template.md`).

### What each hardening step guards against

| Step | Guards against |
|---|---|
| Each fixture runs in a scratch worktree at its pinned `from` commit | a score that silently depends on whatever the current checkout holds, so runs at different times are not comparable |
| `evals/` is removed from the scratch worktree | the agent reading `truth.md` (the answer key) or earlier results |
| The scorer and fixtures are copied out before the first fixture runs, and the copy scores | an agent edit to the scorer or an answer key changing the score |
| A file changed outside `may_change`, or a repo ref created, deleted or moved, marks the fixture `stray` and fails the run | an agent that implements the request, or edits the repo, instead of only classifying it |
| The client never gets `--bare`; the branch's harness config is deployed into the worktree | measuring a model with no harness instead of the `feature-intake` skill under test |

### `eval.json` (one per fixture)

| Key | Meaning |
|---|---|
| `from` | 40-character lowercase commit sha the scratch worktree is checked out at; it must resolve to a commit |
| `may_change` | list of glob patterns for files the agent may create, change or delete. Matching uses `fnmatch`, where `*` also matches `/`. The snapshot ignores `.gitignore`, so list gitignored files intake leaves behind too, such as `specs/*/events.jsonl.lock` from `runtime/run_state.py`; `test_stray_real_fixtures_allow_every_intake_write` checks this against the real run-state script |

### Outputs (in `--output-dir`)

- **`run.json`** — `schema_version`, `model`, `client` (the `claude --version` output, or `unknown`),
  `head` (the commit under test), and per fixture: `from`, `may_change`, `rc` (exit code or
  `"timeout"`), `elapsed` (seconds), `stray` (paths outside `may_change`, plus a `ref:` entry for
  every ref created, deleted or moved — refs cannot be allowed) and `status`
  (`ok`, `stray`, `timeout` or `client-error`).
- **`<fixture>.md`** — the agent's reply, for an `ok` fixture.
- **`<fixture>.raw.txt`** — the raw client output, for any other status.
- **`scorecard.txt`** — the scorer's output.

The runner exits 1 when any fixture is not `ok` or the scorer exits non-zero, else 0.

### Residual risk

The scratch worktree removes `evals/`, but the agent can still read the main checkout or git
history by absolute path (for example `truth.md` in the main checkout, or `git show` of an older
commit). The stray-file check detects writes, not reads. Treat a result as blind only to that
extent.

## Honesty rules

- Report misclassifications plainly. A miss is a finding about the skill (or the fixture's answer
  key), not a failure of the benchmark.
- **Do not re-run a fixture until it passes** — the first scored run is the record.
- If a fixture is found to carry an ambiguous or wrong expected label, revise `truth.md` and note
  the revision here; prior runs are not comparable across the revision.
- The baseline (`results/<date>-baseline.md`) is the regression reference for any future edit to
  `skills/feature-intake/SKILL.md` — note the measured skill commit sha in it.

## Fixture revisions

- **multi-domain (2026-07-17)** — reclassified `high-risk`/`high` → **`normal`/`medium`**. The
  original key claimed "4+ flags → high-risk"; three independent blind runs all returned
  `normal`/`medium`, and re-reading the request confirms only 2–3 flags fire (existing-behavior,
  multi-domain, weak-proof) with one open design choice. The answer key was too aggressive, not the
  skill. `results/2026-07-17-baseline.md`, `-run2`, `-run3` predate this and are **not comparable**
  on this fixture.
