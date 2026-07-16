---
problem_type: bug
module: scripts/harness-audit
tags: bash-set-u, empty-array-expansion, jsonl-parsing, defensive-parsing, advisory-boundary, fix-altitude, harness-scripts, ci-macos-ubuntu
severity: critical
applicable_when: Before iterating a bash array that can legitimately be empty under `set -u` (especially on macOS's bundled bash 3.2, which this repo's CI matrix specifically targets); or whenever a block is advertised as "advisory / never blocks" and you are about to enforce that with a try/except exception list instead of a `|| true` boundary on the command — the list is never provably complete, and this bug shipped twice because of it.
affects:
  - scripts/harness-audit.sh
  - scripts/harness-status.sh
supersedes: null
confidence: high
confirmed_at: 2026-07-13
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
   `set -euo pipefail` — on a malformed line. It took **three** rounds to actually close:
   - Round 1 wrapped `json.loads()` in try/except but left `print(f"...{d['date']}...")`
     outside the try block, so a line that IS valid JSON but missing an expected key (e.g.
     `{"pr":42}`) still raised an uncaught `KeyError` — caught by a second adversarial pass.
   - Round 2 moved the key access inside the `try` and broadened the `except`. **This was
     still wrong, and shipped as if it were done.** `open()` runs *before* the loop, so it is
     outside every `try` in the heredoc: an unreadable log (`PermissionError`) or a non-UTF-8
     byte (`UnicodeDecodeError`) still killed the whole script and silently swallowed the
     Drift Audit section that follows it. Found only on 2026-07-13, by an altitude-angle
     review asking "is this fix deep enough?" — not by any per-line bug hunt.
   - Round 3 (the real fix) put `|| echo "[unreadable: …]"` on the heredoc itself.

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

Bug 2 — each round guarded the failure mode that was top-of-mind and no more. Round 1 guarded
malformed JSON syntax; round 2 guarded the sibling failure in the same statement (valid JSON,
missing key). Both rounds were **enumerating exception types at the wrong altitude**: they
hardened the statement that happened to crash, while the *boundary* — "this advisory section
must never abort the report" — went unenforced. `open()` is not part of any statement they
guarded, so it stayed fatal through both rounds.

The generalizable failure: **an exception-type allowlist can never be proven complete, so it
is the wrong tool for "never fail" semantics.** Every round of `except (A, B, C)` invites the
next `D`. The right altitude is the mechanism that bounds the whole block — here `|| echo` on
the heredoc, which is exactly the convention the same file already used one section below
(`bash harness-audit.sh || true`). The fix was available by *reading the neighbouring code*,
not by enumerating harder.

## Fix

Bug 1 (`scripts/harness-audit.sh`, commit `1eddcbd`): changed
`for f in "${_vnr_files[@]}"; do` to
`for f in "${_vnr_files[@]+"${_vnr_files[@]}"}"; do` — the `${arr[@]+word}` parameter
expansion form only expands `word` (here, `"${_vnr_files[@]}"`) when `arr` is actually set,
so an unset/empty array degrades to zero iterations under `set -u` instead of crashing on any
bash version, 3.2 included.

Bug 2 (`scripts/harness-status.sh`), fixed in three rounds:
- Round 1 (commit `5b506ec`): wrapped `d = json.loads(line)` in
  `try: ... except json.JSONDecodeError: continue` — but left the subsequent
  `print(f"...{d['date']}...{d['findings']}...{d['band']}...")` outside the try block.
- Round 2 (commit `5590288`, found by a later adversarial correctness-review pass): moved the
  `print(...)` call INSIDE the `try:` block and broadened the `except` clause to
  `except (json.JSONDecodeError, KeyError, TypeError): continue`. **Incomplete — do not copy
  this as the fix pattern.** It leaves `open()` unguarded (see round 3).
- Round 3 (2026-07-13, the actual fix): put the failure boundary on the heredoc itself —
  `python3 - "$AUDIT_TREND_LOG" <<'PY' || echo "  [unreadable: $AUDIT_TREND_LOG]"` — plus a
  `[no data rows found]` line for a present-but-empty log. This bounds *every* way the block
  can fail, including the ones nobody enumerated (`PermissionError`, `UnicodeDecodeError`),
  and matches the `|| true` convention already used by the Drift Audit section below it.

## Regression Test

Bug 1: `tests/scripts/harness-audit.test.sh` — new case: "no scripts/run-tests.sh and no
.github/workflows at all -> check 4's file array is empty, must not crash under set -u".
Constructs a fixture root with only a `specs/x/SUMMARY.md` referencing a path-bearing
`### Verify` command and NO `scripts/run-tests.sh`/`.github/workflows/`, then asserts
`bash "$SCRIPT" --root "$d" --json` exits 0.

Bug 2: `tests/scripts/harness-status.test.sh` — added in round 3 (2026-07-13). The absence of
this test through rounds 1 and 2 is *why* the bug survived twice: `run-tests.sh` L1 only runs
`bash -n`, which cannot see inside a quoted `<<'PY'` heredoc, so both incomplete fixes passed
CI green. The suite builds a throwaway fixture repo whose `scripts/harness-audit.sh` is a stub
echoing `DRIFT_AUDIT_RAN`; that sentinel appearing in the output is the proof the trend block
did not abort the script. Eight cases: well-formed · malformed line · valid-JSON-missing-key ·
valid-JSON-non-object · present-but-empty · absent · non-UTF-8 byte · unreadable (bad perms).
The last two fail against the round-2 code — they are the regression lock on this bug class.

## Code Example

```bash
# Bug 1 — bash 3.2-safe empty-array iteration under `set -u`:
# BEFORE (crashes on bash 3.2 when the array is empty):
for f in "${_vnr_files[@]}"; do ...; done
# AFTER:
for f in "${_vnr_files[@]+"${_vnr_files[@]}"}"; do ...; done
```

```bash
# Bug 2 — for "must never fail" semantics, bound the BLOCK; don't enumerate exception types.
#
# ROUND 1 (wrong): guards the one line that crashed → KeyError still fatal.
# ROUND 2 (wrong, and shipped): guards parse + key access → open() still fatal.
#   try:
#       d = json.loads(line)
#       print(f"  {d['date']}    findings={d['findings']}   band={d['band']}")
#   except (json.JSONDecodeError, KeyError, TypeError):
#       continue
#   ...because open() runs BEFORE the loop, outside every try:
#       with open(sys.argv[1]) as f:      # PermissionError / UnicodeDecodeError → exit 1
#
# ROUND 3 (right): the boundary goes on the command, where it bounds everything.
python3 - "$AUDIT_TREND_LOG" <<'PY' || echo "  [unreadable: $AUDIT_TREND_LOG]"
...
PY
```

## Prevention

- For any bash script that runs (or claims to run) under `set -u`: never iterate a
  possibly-empty array with bare `"${arr[@]}"`. Use `"${arr[@]+"${arr[@]}"}"` instead, and
  explicitly test the empty-array branch — on bash 3.2 specifically, since that's what
  `macos-latest` in this repo's CI matrix runs and it behaves differently from bash 4.4+ here.
  Any script advertised as "advisory / never blocks" needs a fixture test that starves it of
  every optional input (no `run-tests.sh`, no `.github/workflows/`, no `specs/`, etc.) to prove
  the empty-input path is actually safe, not just the populated-input path.
- **When a section is advertised as "advisory / never blocks", enforce that at the boundary,
  not with an exception allowlist.** In bash under `set -e`, that means `|| true` (or
  `|| echo "[degraded]"`) on the command itself. An `except (A, B, C)` list is a claim you
  enumerated every failure — you did not, and each round of this bug proved it: round 1 missed
  `KeyError`, round 2 missed `PermissionError`/`UnicodeDecodeError` because `open()` sits
  outside the loop. If you cannot state why the list is exhaustive, you need a boundary, not a
  longer list.
- **Look one section down before inventing a fix.** The correct pattern (`|| true`) was already
  in the same file, eight lines below the bug, for the same "advisory" reason. Two review
  rounds enumerated exception types instead of copying the neighbour.
- **A fix with no regression test is not a fix — and `bash -n` is not a test.** `run-tests.sh`
  L1 cannot see inside a quoted heredoc, so both wrong fixes shipped CI-green. Any change to a
  `scripts/*.sh` block that parses external data needs a case in `tests/scripts/`.
- **Ask "is this fix at the right altitude?" as a distinct review pass.** Every per-line bug
  hunt over this diff — including the harness's own `/correctness-review` — found the parse and
  key-access bugs and missed the boundary. The boundary defect was only found by a reviewer
  asking whether the fix was deep enough or a bandaid. That question is not implied by
  "find the bugs"; it has to be asked on purpose.
