# gh-67-consolidate-lane-evidence — Summary

Lane: high-risk
Confidence: high
Reason: The refactor edits `hooks/commit-quality-gate.sh`, a high-blast commit path that requires high-risk evidence under the CI strict gate.
Flags: high-blast
Affects: scripts/verify_summary.py, hooks/commit-quality-gate.sh, harness-manifest.json, lane-evidence consumers
Input-type: harness improvement

### Intent

> "agree, let do it"

This approval applies to issue #67's item: merge `check_lane_evidence.py` into
`verify_summary.py --lane` while preserving commit-gate behavior.

## What changed

Consolidated lane-to-evidence validation into `scripts/verify_summary.py --lane`, reused the
existing Verify-table parser, switched the commit gate to the consolidated CLI, removed the
standalone validator and test module, and updated tests, manifest contracts, rules, skills, and
operational documentation.

### Rationale

The old scripts independently parsed the same SUMMARY Verify table and maintained matching
placeholder rules. One executable contract removes that drift risk while separate `--lane` and
`--check` modes preserve structural-validation and command-execution semantics.

### Alternatives considered

- Keep both CLIs and extract a shared parser module — rejected because it would add another
  internal surface while retaining two user-facing commands for one SUMMARY contract.
- Fold lane validation into normal `--check` behavior — rejected because lane validation must
  never execute commands and has different exit semantics.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Consolidated CLI resolves prefixed slugs | `bash tests/scripts/spec-prefix-compat.test.sh` | 0 | 5 passed |
| Commit gate preserves staged-file validation | `bash tests/hooks/spec-prefix-compat.test.sh` | 0 | 11 passed |

### Rollback

- Before merge: close PR #150 without merging; no deployed state changes exist.
- After merge: revert the merge commit for PR #150, then run `bash scripts/deploy-harness.sh`
  to restore the prior standalone validator in deployed harness copies.

### Harness-Delta

- The CI failure correctly enforced the existing high-risk SUMMARY requirement. The local full
  suite tests strict-gate behavior in fixtures but does not apply the PR strict gate to the
  current branch diff, so this evidence artifact must be added explicitly for hook changes.
