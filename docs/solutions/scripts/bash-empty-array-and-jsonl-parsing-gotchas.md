---
problem_type: bug
module: scripts/harness-audit
tags: bash-set-u, empty-array-expansion, jsonl-parsing, defensive-parsing, harness-scripts, ci-macos-ubuntu
severity: critical
applicable_when: Before iterating a bash array that can legitimately be empty under `set -u` (especially on macOS's bundled bash 3.2, which this repo's CI matrix specifically targets), or before writing a python except clause that parses an evolving/external file format (JSONL, config, API response) and only anticipates one failure mode you happened to test.
affects:
  - scripts/harness-audit.sh
  - scripts/harness-status.sh
supersedes: null
confidence: high
confirmed_at: 2026-07-04
---

## Problem

Two related crashes surfaced during review of the entropy-trend feature (Wave 4,
`specs/entropy-trend`), both in scripts meant to be advisory/non-blocking:

1. `scripts/harness-audit.sh` check 4 (verify-never-rerun) crashed with `unbound variable`
   and exit 1 on any target root that has neither `scripts/run-tests.sh` nor any
   `.github/workflows/*.yml` file — reproduced by a fixture case in
   `tests/scripts/harness-audit.test.sh`: "no scripts/run-tests.sh and no
   .github/workflows at all -> check 4's file array is empty, must not crash under set -u".
   This is exactly the kind of root `--root <fixture-dir>` legitimately points at in tests,
   and plausibly a fresh/minimal repo running the audit in CI.

2. `scripts/harness-status.sh`'s "Audit Trend" section (a `python3 - <<'PY'` heredoc reading
   `docs/harness-experimental/audit-log.jsonl`) crashed the entire script — under its
   `set -euo pipefail` — on a malformed line. A first fix attempt only wrapped
   `json.loads()` in try/except but left `print(f"...{d['date']}...")` outside the try
   block, so a line that IS valid JSON but missing an expected key (e.g. `{"pr":42}`) still
   raised an uncaught `KeyError` at the print statement — caught by a second, later
   adversarial correctness-review pass, not the first fix.

## Root Cause

Both bugs share one root cause: **narrow defensive coding that catches the tested case, not
the format's full failure space.**

Bug 1 — bash's `set -u` treats `"${arr[@]}"` as an unset-variable reference (not an
empty-array expansion) specifically on bash 3.2, which is macOS's default `/bin/bash` (bash
4.4+ does NOT have this problem — it correctly expands to zero words). The script's own
header promises "advisory, never blocks," but it was only tested/written against roots where
the file-fragment array ended up non-empty — the empty-array path was an untested branch that
only bash 3.2 exposes. This repo's CI matrix runs both `ubuntu-latest` (modern bash) and
`macos-latest` (bash 3.2) for exactly this class of divergence.

Bug 2 — the first fix guarded the ONE failure mode that was top-of-mind (malformed JSON
syntax) but not the sibling failure mode in the same statement (well-formed JSON missing an
expected key). Both failures happen on the same line of Python, but only one was inside the
`try:` block, because the fix was written to satisfy the specific crash observed rather than
to bound the whole operation (parse + key access) that can fail.

## Fix

Bug 1 (`scripts/harness-audit.sh`, commit `1eddcbd`): changed
`for f in "${_vnr_files[@]}"; do` to
`for f in "${_vnr_files[@]+"${_vnr_files[@]}"}"; do` — the `${arr[@]+word}` parameter
expansion form only expands `word` (here, `"${_vnr_files[@]}"`) when `arr` is actually set,
so an unset/empty array degrades to zero iterations under `set -u` instead of crashing on any
bash version, 3.2 included.

Bug 2 (`scripts/harness-status.sh`), fixed in two rounds:
- Round 1 (commit `5b506ec`): wrapped `d = json.loads(line)` in
  `try: ... except json.JSONDecodeError: continue` — but left the subsequent
  `print(f"...{d['date']}...{d['findings']}...{d['band']}...")` outside the try block.
- Round 2 (commit `5590288`, found by a later adversarial correctness-review pass): moved the
  `print(...)` call INSIDE the `try:` block (so both the parse and the dict-key access are
  guarded by the same exception handler) and broadened the `except` clause to
  `except (json.JSONDecodeError, KeyError, TypeError): continue`.

## Regression Test

Bug 1: `tests/scripts/harness-audit.test.sh` — new case: "no scripts/run-tests.sh and no
.github/workflows at all -> check 4's file array is empty, must not crash under set -u".
Constructs a fixture root with only a `specs/x/SUMMARY.md` referencing a path-bearing
`### Verify` command and NO `scripts/run-tests.sh`/`.github/workflows/`, then asserts
`bash "$SCRIPT" --root "$d" --json` exits 0.

Bug 2: `[none]` — no automated regression test was added for `scripts/harness-status.sh`.
This repo has zero existing test coverage for that script; the fix was manually verified by
reproduction (feeding a `{"pr":42}` line followed by a well-formed line through the same
parsing logic and confirming the well-formed line still prints, the malformed one is silently
skipped, and the script proceeds to exit 0). Building a full test harness for
`harness-status.sh` was judged out of scope for this fix.

## Code Example

```bash
# Bug 1 — bash 3.2-safe empty-array iteration under `set -u`:
# BEFORE (crashes on bash 3.2 when the array is empty):
for f in "${_vnr_files[@]}"; do ...; done
# AFTER:
for f in "${_vnr_files[@]+"${_vnr_files[@]}"}"; do ...; done
```

```python
# Bug 2 — guard the WHOLE risky statement, not just the first call in it:
# BEFORE (round 1 — still crashes on a valid-JSON-but-missing-key line):
try:
    d = json.loads(line)
except json.JSONDecodeError:
    continue
print(f"  {d['date']}    findings={d['findings']}   band={d['band']}")
# AFTER (round 2):
try:
    d = json.loads(line)
    print(f"  {d['date']}    findings={d['findings']}   band={d['band']}")
except (json.JSONDecodeError, KeyError, TypeError):
    continue
```

## Prevention

- For any bash script that runs (or claims to run) under `set -u`: never iterate a
  possibly-empty array with bare `"${arr[@]}"`. Use `"${arr[@]+"${arr[@]}"}"` instead, and
  explicitly test the empty-array branch — on bash 3.2 specifically, since that's what
  `macos-latest` in this repo's CI matrix runs and it behaves differently from bash 4.4+ here.
  Any script advertised as "advisory / never blocks" needs a fixture test that starves it of
  every optional input (no `run-tests.sh`, no `.github/workflows/`, no `specs/`, etc.) to prove
  the empty-input path is actually safe, not just the populated-input path.
- For any code that guards a multi-statement operation (parse-then-use, e.g. `json.loads`
  followed by dict-key access) with try/except: put the ENTIRE operation inside the guarded
  block, not just the first call. A narrow try/except that stops at the first line "because
  that's the line that crashed in the reproduction" is a signal to re-scan the rest of the
  block for the same exception class or a sibling one (`KeyError`/`TypeError` alongside
  `JSONDecodeError`) before calling the fix done. Treat "review found a second crash in the
  same statement after round 1" as evidence the first fix pattern (guard-the-symptom vs
  guard-the-operation) needs to become a checklist item in review, not just a one-off fix.
