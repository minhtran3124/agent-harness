---
problem_type: failure
module: scripts/run-tests.sh / scripts/check_verify_rows.py
tags: run-tests, lint-scope, committed-diff, verify-table, strict-gate, green-means-skipped, pre-push, ci-only-failure
severity: critical
applicable_when: You added or edited a specs/*/SUMMARY.md or PLAN.md, ran the suite, saw ALL GREEN, and are about to push — the file-scoped L1 lints did not see your file unless it was already committed.
affects:
  - scripts/run-tests.sh
  - scripts/check_verify_rows.py
  - specs/*/SUMMARY.md
supersedes: null
confidence: high
confirmed_at: 2026-08-12
---
## Applicable When

Authoring or editing a `specs/*/SUMMARY.md` / `PLAN.md` and using `bash scripts/run-tests.sh` as
the pre-push confidence check.

## Symptom

`bash scripts/run-tests.sh` reports `ALL GREEN` locally. The same commit then fails **every** CI
job:

```
tests (ubuntu-latest)   fail    FAILURES — see above     # verify-row lint
tests (macos-latest)    fail
strict-gate (PR)        fail    TIMEOUT [Full suite] command: bash scripts/run-tests.sh (limit: 60s)
                                ✗ no changed high-risk SUMMARY passed verify_summary --check
```

Nothing about the machine differs. The local run printed, several screens up:

```
== L1: verify-row lint (changed SUMMARY/PLAN only) ==
  skip — no changed SUMMARY.md/PLAN.md vs github/simplify
```

## Wrong Approach

Treating `run-tests.sh` → `ALL GREEN` as "CI will pass", when the SUMMARY under test is **written
but not yet committed**. The natural order — write the record, run the suite, then `git add` and
`git commit` — puts the file outside the lint's scope at exactly the moment you check it.

Equally wrong: assuming the lint skipped because the base ref could not be resolved (the usual
shallow-checkout story). `scripts/resolve-base-ref.sh` resolves fine locally; that is not the
mechanism here.

## Why It Failed

`run-tests.sh` scopes the L1 verify-row lint to files that changed **in commits**:

```sh
changed="$(git diff --name-only "$BASE_OUT"...HEAD -- 'specs/*/SUMMARY.md' 'specs/*/PLAN.md')"
```

`git diff BASE...HEAD` compares two commits. An untracked or merely staged file is in neither, so a
brand-new SUMMARY yields an empty `changed` set and the lint prints `skip` — which scrolls past as
one quiet line inside a passing run. CI hits the identical code path *after* the commit exists, so
the file is in scope there and the lint fires. The scoping itself is correct and deliberate
(it keeps the lint off the whole back catalogue); the trap is purely one of timing.

Reproduced both directions on one identical file:

| State of the file | Same lint invocation |
| --- | --- |
| written, not committed | `skip — no changed SUMMARY.md/PLAN.md vs github/simplify` |
| committed | `[Full suite] Verify command runs a full suite/build (>60s strict-gate cap)` |

This is the general shape recorded in `green-can-mean-skipped`: a check that skips and a check that
passes are textually different but visually identical inside a long green run.

## Correct Approach

Run the file-scoped gates **directly against the path**, not through the suite. They take under a
second and do not care whether the file is committed:

```sh
python3 scripts/check_verify_rows.py specs/<slug>/SUMMARY.md
python3 scripts/verify_summary.py --lane <slug>
python3 scripts/verify_summary.py <slug> --check      # what ci-strict-gate re-runs
```

The third command is the one that matters for a high-risk spec: it re-executes every Verify row
under the same 60s cap the strict gate uses, so a row that will TIMEOUT in CI fails here first.

If you prefer the suite, commit first and re-run it — after the commit, the lint is in scope.

## Guardrail

`existing:` `scripts/check_verify_rows.py` already encodes the rule; the gap was reachability, not
detection. `proposed:` make the skip loud rather than quiet — when `changed` is empty *and* the
working tree contains uncommitted `specs/*/SUMMARY.md` / `PLAN.md` changes
(`git status --porcelain -- 'specs/*/SUMMARY.md' 'specs/*/PLAN.md'`), print a warning naming those
paths and the direct command to lint them, instead of the current bare `skip` line.

## Related
- docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md
- docs/solutions/harness/test-and-doc-lint-gate-scope.md
- docs/solutions/harness/wave-boundary-verify-evidence.md
