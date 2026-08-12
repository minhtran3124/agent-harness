# fix-kb-zero-entries-regex — Summary

Lane: high-risk
Confidence: high
Reason: Edits a registered SessionStart hook (`hooks/*` is a high-blast path), even though the
change itself is a two-character regex anchor.
Flags: high-blast
Affects: session-knowledge
Input-type: maintenance

### Intent

> fix luôn cái regex knowledge base đi

Context: the correctness review of `codex-support-phase-5` scored this candidate 0 **as
out-of-range** — the defect predates that branch — and filed it as a real pre-existing repo bug
rather than fixing it inside an unrelated diff. This is that follow-up.

## What changed

`hooks/session-knowledge.sh` detects an empty knowledge base by looking for `0 total entries` in
the INDEX header. The pattern was unanchored, so it also matched the trailing zero of
`30 total entries` — and of any count ending in 0. On this repository (30 entries) the hook
therefore emitted **no knowledge-base context at all**, at every single session start, while
looking exactly like a healthy silent-when-empty hook.

The fix anchors the leading boundary: `(^|[^0-9])0 total entries`.

### Rationale

This is the failure mode the repo already has a name for: a check that skips looks identical to a
check that passes. Nothing surfaced it because both states produce silence, the suppression is
non-blocking by design, and the entry count only crossed a multiple of ten as the store grew.
Measured before and after on the real INDEX: 0 chars of knowledge-base context → 11,227 chars.

### Alternatives considered

- **Drop the header heuristic and rely on the data-row scan below it** — rejected; the row scan
  already runs and the header check is a cheap early exit for a genuinely empty rebuild. Removing
  it would change behavior for the bootstrap-placeholder case the tests pin.
- **Parse the count as an integer** — rejected as more code than the defect warrants; the anchor
  restores the intended semantics exactly.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Hook contract | `bash tests/hooks/session-knowledge.test.sh` | 0 | 13 assertions incl. the new count-ending-in-zero regression |
| Full suite | `bash scripts/run-tests.sh` | 0 | 514 Python tests, ALL GREEN |

The new test is load-bearing, verified by mutation: with the hook reverted and the test kept, the
suite reports `12 passed, 1 FAILED`; with the fix in place, 13 pass.

### Not auto-verified

- **Deployed consumers are not re-checked here (traceability).** The fix lands in the source hook;
  repositories that already installed an older copy keep the buggy regex until they re-sync.
- **Only the `0 total entries` header form is covered (traceability).** The separate
  placeholder-row and missing-INDEX emptiness paths are unchanged and still covered by their
  existing assertions.

### Rollback

- `git revert <sha>` — the change is one regex anchor plus one test; reverting restores the prior
  (suppressing) behavior with no data or state migration.
