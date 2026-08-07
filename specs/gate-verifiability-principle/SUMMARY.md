# gate-verifiability-principle — Summary

Lane: tiny
Confidence: high
Reason: docs-only, one file (CLAUDE.md), no new public callable; CLAUDE.md is outside the workflow-engine and high-blast hard-gate surfaces
Flags: none
Affects: none
Input-type: harness improvement

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

"review ảnh hiện tại, đúc kết ra kiến thức từ đó, sau đó so sánh với repo harness hiện tại trên branch simplify. Xem xét thử chúng ta có thể học và áp dụng dc gì ở đây." (HERMES v0.20 grounded-citations infographic)

Scope decided by user selection: "Làm B+C (tiny) trước — thêm panel 'Code-verifiable / Not auto-verified' vào template + 1 dòng principle 3-tầng vào CLAUDE.md. Không động vào xia2."

## What changed

CLAUDE.md gained a short "Gate verifiability" subsection under Hooks: every gate
enforces exactly one evidence tier — traceability (structure matches), provenance
(evidence re-derived from the source of truth), or truth (behavior re-run) — and new
gates must document `Verifies:` / `Does not verify:` lines.

`templates/SUMMARY.template.md` gained the matching `### Not auto-verified` panel:
`### Verify` is the code-verifiable half, the new section is the negative scope —
claims this change makes that no gate checks, each labelled with the tier it reached.

### Rationale

The repo already operates this tier separation ad-hoc (Integration Evidence Tiers,
"evidence exists vs evidence is honest — do not conflate"); naming it once in
CLAUDE.md gives reviewers a vocabulary and stops over-claiming, adopting the HERMES
v0.20 model (TRACEABILITY ≠ VERIFIED PROVENANCE ≠ TRUTH).

### Alternatives considered

- New `templates/GATE.template.md` — rejected: adds a file and a sync surface for a
  two-line convention; the CLAUDE.md hook section is where gates are already documented.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| doc-truth lint | `bash scripts/lint-doc-truth.sh` | 0 | paths + hook table consistent | |
| harness suite | `bash scripts/run-tests.sh` | 0 | template change parse-safe for both consumers | |
| contract consumers | `bash scripts/check-contract-impact.sh templates/SUMMARY.template.md` | 0 | verify_summary.py + commit-quality-gate.sh | |
| lane evidence | `python scripts/verify_summary.py --lane gate-verifiability-principle` | 0 | tiny-lane evidence present | |

### Not auto-verified

- The `### Not auto-verified` panel is a prose convention — no gate requires the section
  to exist or checks that its claims are complete. Reached **traceability** only
  (the section is present in the template and in this SUMMARY); nothing re-runs it.
- The CLAUDE.md principle text is not machine-enforced: no lint asserts that a new gate
  ships `Verifies:` / `Does not verify:` lines. Reached **traceability**; enforcement
  would need a new doc-truth rule, deliberately out of scope for this tiny lane.

### Rollback

- `git revert <sha>` (docs-only)

### Harness-Delta

- none
