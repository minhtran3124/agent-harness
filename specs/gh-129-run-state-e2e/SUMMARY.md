# gh-129-run-state-e2e — Summary

Lane: normal
Confidence: high
Reason: adds one new test file under `tests/scripts/`; no engine, hook, or settings change — no hard gate fires.
Flags: none
Affects: `runtime/run_state.py` (test coverage only — the engine itself is unmodified)
Input-type: change request

### Intent

> i want to create a real test case and running testing for real case. Capture the jsonl was generated and show for me.

> tao test that trong repo di

## What changed

Adds `tests/scripts/run-state-e2e.test.sh` — 15 assertions that drive the real
`runtime/run_state.py` CLI through a complete realistic run (intake → plan → implement →
CI failure → fix → review round → ship, 15 checkpoints) inside a `mktemp` sandbox, then assert
on the durable artifacts the harness checkpoints actually leave behind. No engine change; no
change to `scripts/run-tests.sh` (the runner already globs `tests/scripts/*.test.sh`, and the
new suite was confirmed auto-discovered).

What it covers that `runtime/test_run_state.py` does not: the pytest suite tests each function
and rule in isolation, so it cannot catch a defect that only appears after a long state chain.
This suite asserts **log-shape and whole-run properties** — seq contiguity across all 15 events,
`from_state` chaining to the previous `to_state`, the full required-key set on every line,
sorted-key serialization (diff stability), `waiting_on` present on every waiting-state entry —
plus the **append-nothing invariant**: a refused transition must leave the log byte-identical.
A run that only ever receives refused transitions keeps a 1-line log.

### Rationale

Written as a shell suite under `tests/scripts/` rather than more pytest cases because the thing
under test is the CLI contract as the harness checkpoints invoke it (argv → exit code → files on
disk), not the Python API. The engine resolves `specs/<slug>` relative to CWD and has no
`--specs-root` flag, so each case runs inside its own `mktemp` dir — hermetic, nothing in the
real repo is touched.

### Alternatives considered

- Add the cases to `runtime/test_run_state.py` — rejected: that suite exercises the Python
  functions; this one must exercise the CLI surface and the files it leaves behind.
- Wire the suite explicitly into `scripts/run-tests.sh` — unnecessary: `tests/scripts/*.test.sh`
  is already globbed (both for shellcheck at line 12 and execution at line 48). Confirmed by
  observing `== tests/scripts/run-state-e2e.test.sh ==` in a full-runner run.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| new e2e suite | `bash tests/scripts/run-state-e2e.test.sh` | 0 | 16 passed (after the review round below) | |
| auto-discovery by the runner | `bash scripts/run-tests.sh` | 0 | ALL GREEN; output contains `== tests/scripts/run-state-e2e.test.sh ==` → `15 passed`, plus 214 python tests | |
| mutation M1 — drop `sort_keys` on the append path (line 290) | `bash tests/scripts/run-state-e2e.test.sh` | 1 | 14 passed, 1 FAILED — killed by the diff-stability assertion | |
| mutation M3 — `seq` increments by 2 (line 348) | `bash tests/scripts/run-state-e2e.test.sh` | 1 | 12 passed, 3 FAILED — killed by seq-contiguity, projection, and replay assertions | |

Mutation results follow `docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md`:
a green suite is not evidence until a deliberate defect makes it red. The engine was restored via
`git checkout -- runtime/run_state.py` after each mutant and is unmodified in this change.

**Disclosed non-kill (M2).** Replacing the terminal-state guard at `runtime/run_state.py:216`
with `if False:` does **not** fail this suite — nor the existing pytest suite (29 passed under the
mutant). The `valid_targets()` check immediately below catches it anyway, because
`FORWARD_TRANSITIONS` has no key for any terminal state, so the observable behavior (exit 2,
nothing appended) is unchanged; only the error message differs. That guard is therefore redundant
defense-in-depth, not dead code with a behavioral gap. Not fixed here — reporting it rather than
silently adding a message-coupled assertion, which would be a brittle test of wording.

### Review round — PR #171 (Codex, 3 × P2, all accepted)

All three findings were verified against the engine before fixing; all three were real.

| # | Finding | Verification | Fix |
| --- | --- | --- | --- |
| C1 | The append-nothing assertions used `wc -l`, which cannot see an in-place rewrite or an append with no trailing newline — contradicting the suite's own "byte-identical" claim | Demonstrated: a 3-line file rewritten to different 3-line content keeps `lines=3` while `cksum` changes `2923054182 6` → `317754081 13` | Added a `digest()` helper (`cksum`, POSIX / macOS + Linux); all four refusal + replay assertions now compare byte fingerprints |
| C2 | `resume_event` is in the engine's event schema but was missing from the "full required key set" assertion | Confirmed in `runtime/run_state.py:285,356`; all 15 events in a live run carry it | Added to the required-key set |
| C3 | The `list --active` assertion ran in a sandbox holding no terminal run, so it would pass even if `--active` stopped filtering | **Decisive**: the pre-fix suite scores `15 passed` under mutant M5 (filter deleted) — genuinely vacuous | Both runs now live in the same specs root; added a companion assertion that plain `list` *does* show the shipped run, proving the filter is what hides it |

Mutation evidence for the fixes (engine restored via `git checkout --` after each):

| Mutant | Pre-fix suite | Post-fix suite |
| --- | --- | --- |
| M4 — CLI stops serializing `resume_event` (`:356`) | not covered | **killed** — 15 passed, 1 FAILED |
| M5 — `list --active` stops filtering terminal runs (`:401`) | **survived** (15 passed) | **killed** — 15 passed, 1 FAILED |

### Rollback

- `git revert <sha>` — adds one test file, touches nothing the harness executes at runtime.

### Harness-Delta

- none
