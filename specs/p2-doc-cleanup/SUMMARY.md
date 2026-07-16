# p2-doc-cleanup — Summary

Lane: normal
Confidence: high
Reason: Docs-only cleanup of remaining phantom references from the harness audit; no risk flags, no hard gate.
Flags: none
Input-type: harness improvement

## What changed

Removed the phantom `skills/_archive/xia/` section and amended the "per-skill READMEs
removed" claim in `skills/README.md`; repointed `docs/harness-experimental/` research
links in `HARNESS.md` to the upstream GitHub repo; scaffolded the trust-metrics ledger
at `docs/harness-experimental/trust-metrics.md` (referenced as load-bearing by
feature-intake, orchestration.md, and the SUMMARY template); dropped the gitignored
`specs/workflow-upgrade/PLAN.md` example pointer in `rules/plan-format.md`; dropped the
phantom "standalone .md graph skills" mention in `README.md`.

### Rationale

Same doc-truth class as P1: tracked docs referenced paths that don't exist. Research
links point upstream (where the research actually lives); the ledger is scaffolded
rather than de-referenced because three docs treat it as a real mechanism.

### Alternatives considered

- Delete `skills/compound/README.md` + `skills/xia2/README.md` to make the original
  claim true — rejected: 372 lines of operational detail not fully merged into
  skills/README.md; amending the claim is lossless.
- Remove the ledger references instead of scaffolding the file — rejected: the ledger
  is part of the harness design (trust calibration), not an accidental mention.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes |
| --- | --- | --- | --- |
| No phantom path refs remain | `grep -rn "harness-experimental\|_archive\|workflow-upgrade" <tracked docs>` | 0/1 | only hits: GitHub URLs, the now-real ledger, and a historical note in visual-planner/SKILL.md:220 |
| Ledger exists | `ls docs/harness-experimental/trust-metrics.md` | 0 | |
| `.claude/` clone resynced | `bash scripts/deploy-harness.sh && diff -rq skills/ .claude/skills/ && diff -rq rules/ .claude/rules/` | 0 | |

### Rollback

- `git revert 2582d64`

### Harness-Delta

- backlog — same drift-lint proposal as P1 (assert referenced repo paths exist in CI/hook).
