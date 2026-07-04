<!-- Header is machine-read by risk-corroboration.sh (Lane) + trust-metrics ledger. -->

# verify-substance — Summary

Lane: high-risk
Confidence: high
Reason: Hard gate by precedent — touches scripts/run-tests.sh (the CI contract, treated high-blast in the p3jk ledger row) and the evidence-verification engine the strict gate depends on.
Flags: existing-behavior, weak-proof
Affects: scripts/verify_summary.py, scripts/test_verify_summary.py, scripts/check_lane_evidence.py, scripts/test_check_lane_evidence.py, scripts/run-tests.sh
Input-type: harness improvement

> Lane drives ceremony; Confidence drives interruption. Direction fixed by the deep review
> findings (each verified with a concrete repro), so confidence is high.

### Intent

Phase 3 của harness v0.3 (docs/harness-v03-plan-overview.md, Wave 2): siết substance cho evidence.
Deep review đã chứng minh: (DR-6) ci-strict-gate pass được bằng row `| x | true | 0 | |` — "một lệnh
exit 0" không phải bằng chứng; rollback bằng template chưa sửa (`git revert <sha>`) được
check_lane_evidence chấp nhận; (DR-7) test_verify_summary.py không bao giờ được run-tests.sh chạy →
parser của CI gate không có coverage trong CI; (DR-18) placeholder set có em-dash lặp (một cái đáng
lẽ là ASCII `-`), lệch với check_lane_evidence; (DR-19) 3 semantics trap: (a) row khai exit≠0 trung
thực vẫn FAIL kể cả khi claimed==actual — negative-proof không biểu diễn được; (b) write-mode stamp
`Verified:` cả khi checks FAILED; (c) _rewrite_table map theo tên check → tên trùng thì collide.
Kèm (DR-Low) check_lane_evidence lane match substring: `Lane: not-normal` resolve thành `normal`.
Fix tất cả + thêm test_verify_summary.py vào run-tests.sh (1 dòng).

## What changed

- **`verify_summary.py`** — (1) **trivial-command denylist**: a whole-command `true`, `:`, `exit 0`,
  or bare `echo …` is reported `TRIVIAL` and FAILS the check — exit-0 of a no-op is not evidence
  (closes the `| x | true | 0 | |` forgery through ci-strict-gate); (2) placeholder set fixed to
  `{"—", "–", "-", "<command>", ""}` (duplicate em-dash was a typo'd ASCII hyphen — now aligned with
  check_lane_evidence); (3) **negative proof representable**: a row PASSES when claimed == actual,
  even non-zero (a check that *should* fail can now be pinned); FAIL only on mismatch or unclaimed
  non-zero; (4) `Verified:` timestamp is stamped **only when all checks pass**; (5) `_rewrite_table`
  maps results by row order, not check name — duplicate names no longer collide.
- **`check_lane_evidence.py`** — (6) lane resolves by **exact match** (`tiny|normal|high-risk` as the
  whole value; `not-normal` or the raw template line no longer resolve); (7) a Rollback consisting
  ONLY of the unedited template line (`git revert <sha>`) no longer counts — high-risk needs a real
  rollback.
- **`run-tests.sh`** — `scripts/test_verify_summary.py` added to PYTESTS (DR-7: the one script the
  CI strict gate depends on finally has CI coverage).
- Tests updated/added in both test files for every behavior above.

### Rationale

The strict gate's promise is "machine-verified proof"; the deep review showed the proof was
trivially satisfiable (a `true` row) and the semantics penalized honesty (a truthful non-zero claim
failed). These fixes make the gate check *substance* where mechanical, keep honest claims
expressible, and put the gate's own parser under CI.

### Alternatives considered

- Require every verify command to reference a changed path from the PR diff — deferred: needs diff
  context plumbed through ci-strict-gate and risks false-blocks on legit whole-suite commands
  (`run-tests.sh` references no changed path). The trivial-denylist closes the known forgery with
  far less false-positive surface. Backlogged for entropy-phase consideration.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| harness test suite | `bash scripts/run-tests.sh` | 0 | ALL GREEN — 145 py (incl. test_verify_summary, now wired: DR-7) + all bash suites |
| DR-6 forgery blocked at gate level | `bash tests/scripts/ci-strict-gate.test.sh` | 0 | 9 passed — incl. the new pinned case: a high-risk SUMMARY whose only Verify row is `true` → gate BLOCKS |

### Rollback

- Revert the PR: `git revert <merge-sha>` (pure scripts; no persisted state; ci-strict-gate falls
  back to prior semantics).
- Per-file: `git checkout HEAD~1 -- scripts/verify_summary.py scripts/check_lane_evidence.py scripts/run-tests.sh scripts/test_verify_summary.py scripts/test_check_lane_evidence.py`

### Review outcomes

- **correctness-review** (Opus) — found 1 MEDIUM real bug, **fixed**: `_rewrite_table` lacked the
  parser's `startswith("<")` skip arm, so a `<todo …>` placeholder row between real rows shifted
  the result queue — a fabricated exit landed on the placeholder and the last real row silently
  kept its unverified claim (file record only; the gate verdict itself was computed correctly).
  Fixed by mirroring the exact parse skip criteria + a pinned regression test. LOW note addressed:
  the trivial denylist is best-effort (wrapped no-ops like `(true)`, `/usr/bin/true` still pass) —
  documented in the regex header as "not a security boundary; removes the laziest forgery class".
  All other probes confirmed sound (mid-table alignment, stale-stamp drop, template-rollback regex,
  fixture edits, no new execution surface).
- **intent-review** (independent model) — PASS; all DR items met except one residual it caught,
  **fixed**: DR-18 was half-done (en-dash added to verify_summary's placeholder set but not
  check_lane_evidence's, and my "identical" comment was false). Now both sets match and a
  cross-checker test pins them identical permanently. No excess, no drift.

### Harness-Delta

- backlog — "verify command must reference the diff" (stronger substance check) deferred to the
  entropy phase; needs changed-file plumbing in ci-strict-gate and an allowlist for whole-suite
  commands.
