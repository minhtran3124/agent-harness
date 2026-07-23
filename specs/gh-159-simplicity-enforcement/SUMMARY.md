# gh-159-simplicity-enforcement — Summary

Lane: high-risk
Confidence: high
Reason: All four touched files are workflow-engine surface (skills/*/SKILL.md, a dispatch prompt, and hooks/risk-corroboration.sh) — hard gate per harness-manifest.json, warn-mode at commit but classified high-risk at intake regardless.
Flags: workflow-engine
Affects: subagent-driven-development ship chain, intent-review excess classification, implementer dispatch prompt, risk-corroboration.sh
Input-type: harness improvement

### Intent

check gh issue https://github.com/minhtran3124/agent-harness/issues/159
- new spec/ folder and create design + plan files

(Full issue body + the issue author's own follow-up audit comment — design decisions D1-D5,
current-state table, wave-1/wave-2 split — are condensed in `design.md`; the issue itself is the
verbatim source of the acceptance criteria this plan implements.)

## What changed

Wires simplicity enforcement into the existing ship path instead of adding new gates: a
threshold-triggered `/simplify` pass runs before `/correctness-review`, `intent-review`'s
`excess` definition now names config knobs/new public surface explicitly, the implementer
dispatch prompt restates Simplicity First constraints up front, and `risk-corroboration.sh`
gains a warn-only diff-size note suggesting `/simplify` when a diff is disproportionate to its
declared lane.

### Rationale

The issue's own follow-up comment already audited the current tree and proposed D1-D5 (one
existing skill, not three; insertion point before correctness-review; a threshold trigger
instead of lane-manual; warn-only diff-size signal) — implementing that plan directly rather than
re-deriving it avoids relitigating decisions the repo owner already made with file:line evidence.

### Alternatives considered

- A new dedicated hook for the diff-size signal — rejected per the issue's explicit scope note
  (strengthen existing hooks/skills, no new hook).
- Gating `/simplify` on lane alone (manual for tiny) — rejected in favor of D4's line-count
  threshold, which is strictly stronger (still catches an oversized tiny-lane diff).

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| baseline | `bash scripts/run-tests.sh` | 0 | ALL GREEN before implementation (185 python tests + shell suites) | |

### Rollback

- `git revert <sha>` (per task commit, or the wave-boundary commit if squashed)

### Harness-Delta

- none
