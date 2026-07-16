# harness-tests-phase1 — Summary

Lane: high-risk
Confidence: high
Reason: Work is additive test infra (no hooks/ edits), but risk-corroboration's high-blast regex `(^|/)hooks/` matches the new tests/hooks/*.test.sh paths — lane raised to corroborate the mechanical gate; human approved the work explicitly. Regex refinement flagged in Harness-Delta.
Flags: none
Input-type: harness improvement

## What changed

Phase 1 of the harness test strategy: a hermetic bash test framework (`tests/lib.sh` —
throwaway git repos, hook stdin contract, assertion helpers), contract tests for the three
riskiest hooks (`risk-corroboration`, `commit-quality-gate`, `auto-test-on-change` — the
session's ad-hoc matrices frozen as regression tests), the installer 6-case suite, a
doc-truth lint (`scripts/lint-doc-truth.sh` — referenced paths exist + CLAUDE.md hook table
vs settings.json registration), a single entry point (`scripts/run-tests.sh`), and a
GitHub Actions workflow (ubuntu + macos matrix).

### Rationale

Every verification this session was ad-hoc and discarded after use; nothing prevents the
next change from regressing what was just fixed. Hooks have a pure contract (stdin JSON →
exit code + stderr) so they test like units. Plain bash (no bats dependency) matches the
harness's jq-only dependency philosophy. The doc-truth lint mechanizes the audit that
started this whole branch — third drift would be caught at CI, not by a human re-audit.

### Alternatives considered

- bats-core as the test framework — rejected: adds an install step everywhere for TAP
  output we don't need; a 60-line lib.sh covers it.
- Wiring the lint into commit-quality-gate.sh — deferred: that file is a hard-gate hook;
  phase 1 stays additive. CI covers the gap.

### Deviations

- none

### Known bugs surfaced (NOT fixed — hooks/* hard gate, awaiting approval)

- `commit-quality-gate.sh:136` has the same `|| true; RESULT=$?` bug fixed in P3 for
  auto-test: pytest failures can never block the commit. Covered by an xfail test.
- The `≥5 app/ files → /compound hint` is unreachable unless matching test files exist
  (early exit at "No matching test files"); test documents actual behavior.

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| Full suite | `bash scripts/run-tests.sh` | 0 | 40 passed, 1 xfail (commit-gate `\|\| true` bug), skips none on this machine |
| Lint negative check | inject `[ghost](docs/does-not-exist.md)` + `hooks/ghost-hook.sh` into README → lint | 1 | both flagged; pass again after restore |
| Workflow YAML parses | `python3 -c "yaml.safe_load(...)"` | 0 | |
| Hermeticity | all fixtures under mktemp; repo `git status` unchanged by suite | 0 | |
| Clone resync | `bash scripts/deploy-harness.sh` | 0 | |

### Rollback

- `git revert 0bf8daa` (additive files only)

### Harness-Delta

- backlog — risk-corroboration's high-blast path regex `(^|/)hooks/` false-positives on
  `tests/hooks/` (and would on any `*/hooks/` subtree). Candidate fix: anchor to repo-root
  `^hooks/` (+ `^\.claude/hooks/`); needs the hooks/* hard-gate approval to change.
