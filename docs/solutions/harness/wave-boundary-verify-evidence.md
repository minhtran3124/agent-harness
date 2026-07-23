---
problem_type: knowledge
module: hooks/commit-quality-gate.sh (Check 1.6) + specs/<slug>/SUMMARY.md
tags: [lane-evidence, verify-table, wave-parallelism, commit-hook, staged-copy, activation-gap]
severity: standard
applicable_when: Executing any multi-wave plan whose commits stage files under specs/<slug>/ in a repo with commit-quality-gate.sh wired (every normal/high-risk lane task).
affects:
  - hooks/commit-quality-gate.sh
  - templates/SUMMARY.template.md
supersedes: null
confidence: high
confirmed_at: 2026-07-23
---
## Applicable When

Executing any multi-wave plan whose commits stage files under `specs/<slug>/` in a repo with
`commit-quality-gate.sh` wired (every normal/high-risk lane task).

## Pattern

Wave-boundary evidence: fill the SUMMARY `### Verify` table incrementally, per wave — never batch
it at the end.

## How to Use

Check 1.6 triggers on **any** staged path under `specs/<slug>/` (not only SUMMARY.md itself) and
judges the **indexed** copy of SUMMARY.md. So every mid-implementation commit touching the spec
dir must already carry lane evidence: for normal/high-risk, at least one non-placeholder
`### Verify` row. At the end of each wave, add rows ONLY for checks actually run in that wave
(command + real exit code), stage the updated SUMMARY.md with the wave's code, then commit.

## Code Example

```markdown
| Check | Command | Exit | Notes | Criterion |
| Hook contract tests | `bash tests/hooks/risk-corroboration.test.sh` | 0 | 27 passed — wave 1 | SC-1 |
```
(rows appended per wave; the "— wave N" note marks when it actually ran)

## Gotchas

- The gate checks the STAGED SUMMARY — adding the row without `git add` does not unblock.
- Verify rows must be pipe-free and <60s; the full suite goes in prose below the table, not in a
  row (see verify-row-must-be-pipe-free-and-under-60s.md — reintroduced and re-caught this session).
- Activation gap (meta-repo): the LIVE hooks are the deployed `.claude/hooks/` copies; editing
  `hooks/` source changes nothing at runtime until a human-confirmed `scripts/deploy-harness.sh`
  re-sync. Any plan changing `hooks/` needs an explicit activation step or the fix silently never
  takes effect.

## Related

- docs/solutions/harness/verify-row-must-be-pipe-free-and-under-60s.md
- docs/solutions/harness/deploy-harness-does-not-prune-deleted-orphans.md — same source-vs-deployed divergence root
