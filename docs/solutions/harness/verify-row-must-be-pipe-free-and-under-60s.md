---
problem_type: failure
module: verify_summary / ci-strict-gate
tags: verify-table, summary-md, pipe-cell-split, strict-gate, timeout, plan-format-guardrail, machine-verified-proof
severity: critical
applicable_when: Writing a `### Verify` row in a spec SUMMARY.md — before you paste any command containing a pipe character or a whole-suite/build invocation.
affects:
  - specs/*/SUMMARY.md
  - scripts/verify_summary.py
  - scripts/ci-strict-gate.sh
supersedes: null
confidence: high
confirmed_at: 2026-08-17
---
## Applicable When

Authoring any `### Verify` table row in `specs/<slug>/SUMMARY.md`. Two independent failure modes bite the same table.

## Symptom

- `verify_summary.py --check <slug>` reports `MISMATCH … claimed=None actual=<n>` or `FAIL` for a row whose command is *correct* and passes when run by hand. (Hit 6× in one session.)
- On a **high-risk** spec (diff touches a strict-gate hard-gate path — `settings.json`, `hooks/`, `render_plan.py`, `templates/`), CI's `strict-gate` job prints `TIMEOUT [<row>] (limit: 60s)` then `BLOCKED`, even though local `run-tests.sh` finishes in seconds. (Hit 1× on PR #98.)

## Wrong Approach

1. **Pipes inside a Verify command.** `verify_summary.parse_verify_table` splits each markdown row on `|`. Any `|` in the command — an alternation `grep -E "a|b"`, a logical `||`, a real pipe `ls | wc -l`, even `&&` next to a pipe — is read as a *column boundary*, so the parser sees a truncated command (or shifts the Exit column) → the row can never match its claimed exit.
2. **A whole-suite/build as a Verify row.** `| full suite | bash scripts/run-tests.sh | 0 |`. `ci-strict-gate.sh` re-runs every Verify command under a **60s per-command cap**; a cold CI runner exceeds it → TIMEOUT → the gate blocks the PR.

## Why It Failed

The Verify table is *data parsed by machine*, not prose: `|` is its delimiter, and each row is a bounded proof re-executed by the gate. A pipe is a delimiter collision; a full suite violates `rules/plan-format.md` Guardrail 3 ("Verify <60s — if longer, split into sub-tasks") — the same 60s the strict gate enforces. The full suite is already covered by CI's `tests` job (ubuntu + macos), so as a Verify row it is both redundant and self-defeating.

## Correct Approach

Every Verify command must be **pipe-free** AND **<60s re-runnable**:

- Replace `grep -E "a|b|c"` with `grep -e a -e b -e c` (no `|`).
- Replace `X || r=1` / `X && Y` chains with `X; a=$?; Y; b=$?; test "$a" = 0 -a "$b" = 0` (capture `$?`, combine with `test -a`).
- Replace `cmd | wc -l` / `cmd | python -c …` with a redirect: `cmd > /tmp/out; <read /tmp/out without a pipe>`.
- Never make the full suite / a long build a Verify row — cite it in a prose note ("covered by the CI `tests` job") instead. Put fast, specific checks in the table (one test file, a grep-guard, a lint, a single re-run).

## Guardrail

`existing:` `scripts/check_verify_rows.py`, wired into `run-tests.sh` L1, scans every changed `specs/*/SUMMARY.md` / `PLAN.md` `### Verify` command cell and fails on (a) a literal `|` in the command, and (b) a whole-suite/build invocation.

**Phrase-collision caveat (2026-08-17, test-layer-ladder):** the whole-suite detector
`_OTHER_SLOW` matches the literal `full[ -]suite` **anywhere in the command cell**, not only as
an executed invocation. A Verify/SC row that greps *prose containing that phrase* —
`grep -q "Never put the full suite" rules/plan-format.md` — false-positives and fails L1, so a
rule sentence written with "full suite" becomes the one phrase in the repo that cannot be
grep-pinned. When authoring rule prose that SC rows may later pin, prefer "whole suite" (not
matched), or pin a different substring of the sentence.

**Reachability caveat (2026-08-12, PR #202):** that L1 step is scoped to files changed *in commits* (`git diff BASE...HEAD`), so it does not see a SUMMARY that is written but not yet committed — the usual authoring order. A whole-suite row therefore still reached CI and blocked all three jobs while local `run-tests.sh` said `ALL GREEN`. Lint the path directly before pushing (`python3 scripts/check_verify_rows.py specs/<slug>/SUMMARY.md`, and `python3 scripts/verify_summary.py <slug> --check` for the strict-gate re-run). See `committed-diff-scoped-lint-skips-uncommitted-work.md`.

## Related
- docs/solutions/harness/committed-diff-scoped-lint-skips-uncommitted-work.md
- docs/solutions/harness/mutation-testing-proves-a-suite-is-load-bearing.md
- docs/solutions/scripts/bash-empty-array-and-jsonl-parsing-gotchas.md
