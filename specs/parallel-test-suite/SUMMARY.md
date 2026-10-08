# parallel-test-suite — Summary

Lane: normal
Confidence: high
Reason: test-runner and CI-step change only; no hook, gate, or settings logic touched; reversible by revert.
Flags: none
Affects: scripts/run-tests.sh, .github/workflows/harness-ci.yml
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

> now, make the review the workflow script of current harness. I saw have a lot of scripts and not sure some one of them block or make slow down performance or even no need it

> do 1,2,3 first

> make sure CI local pass and open PR

The review measured the hooks (5–25 ms per call, ~120 ms per commit — not a bottleneck) and found
the cost in `scripts/run-tests.sh`: ~135 s serial on a 20-core machine. Items 1–3 were: run the
shell suites in parallel, stop running the Codex contract twice in CI, parallelize pytest.

## What changed

- `scripts/run-tests.sh` runs the 55 hermetic shell suites in parallel (`xargs -P`, one log per
  suite, replayed in glob order so output and the FAILURES summary read as before).
- The shared pytest venv is built once up front, before any concurrency, so first-run suites
  cannot race on venv creation + pip install. `pytest-xdist` is installed best-effort and pytest
  uses `-n <jobs>` only when it imports.
- New knobs: `HARNESS_TEST_JOBS` (default: CPU count; `1` = serial) and `HARNESS_SKIP_SUITES`
  (space-separated suite paths to skip, each printed as a named skip).
- `harness-ci.yml` sets `HARNESS_SKIP_SUITES` for `codex-alpha-contract.test.sh`, which already
  runs as its own named CI step — saves ~12 s per OS runner.

Measured locally: full suite ~135 s → ~25 s (pytest 24 s → 5 s); ~29 s on a fresh `TMPDIR`
including the venv build.

### Rationale

Every suite works in its own `mktemp` repo (`tests/lib.sh` design note), so parallelism needs no
suite changes; the only shared resource is the pytest venv, now warmed serially first.

### Alternatives considered

- Drop the explicit Codex CI step: rejected — its comment makes it a deliberately named CI result.
- Make pytest-xdist a hard requirement in `ensure_pyenv`: rejected — would make every suite's
  venv check depend on a plugin only `run-tests.sh` uses.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| runner syntax | `bash -n scripts/run-tests.sh` | 0 | | |
| CI skips the duplicate suite | `grep -q 'HARNESS_SKIP_SUITES: tests/scripts/codex-alpha-contract.test.sh' .github/workflows/harness-ci.yml` | 0 | | |
| runner wires the skip + jobs knobs | `grep -q 'HARNESS_TEST_JOBS' scripts/run-tests.sh` | 0 | | |

The full suite (`scripts/run-tests.sh`) passed locally 5 times in a row: ALL GREEN, 781 pytest
passed, worktree unchanged after each run. A deliberately failing temp suite made the run exit 1
and was named under FAILURES; the skip knob printed its named skip line.

### Advisory Findings

- Suites leak `tmp.*` dirs into `TMPDIR` (seen when run with a fresh `TMPDIR`). Each suite is
  invoked exactly as before, so this is believed pre-existing; not investigated here.

### Intent Findings

- none

### Not auto-verified

- Suites are free of cross-suite interference under parallelism — reached truth only by 5 green local runs on Linux; macOS CI is the first run there.
- The ~25 s figure — reached truth on one 20-core machine; CI runners have fewer cores.

### Rollback

- `git revert <sha>`, or set `HARNESS_TEST_JOBS=1` to restore a serial run without reverting.

### Harness-Delta

- none
