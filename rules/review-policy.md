---
paths:
  - "specs/*/SUMMARY.md"
---

# Review Policy

Applies to the task reviewer and intent review. It gives their findings one
vocabulary and changes no reviewer's oracle, inputs, output schema or blocking rules.

## Important or Nit

An Important finding blocks. It enters a fix round, or it is escalated where the owning skill routes
it that way (a Rule 4 finding, an ambiguous gap). A Nit is listed and never blocks.

| Reviewer | Important | Nit |
|---|---|---|
| Task review | `Critical`, `Important` | `Minor` |
| Intent review | `gap`, and `drift` that changes behavior | `drift` that is equivalent. `excess` is report-only |

## Nit reporting

Report every Nit. There is no count cap. Keep each Nit in your existing findings list under its
existing severity or class. The controller never opens a fix round for a Nit and records it in
SUMMARY.

## Do not report

- Findings in generated files: `PLAN.html`, `.plan-review.json`, deployed harness copies, and
  `*.lock` files.
- Lint and format findings that a linter or formatter wired into the project's CI or hooks already
  checks. A runtime bug with a concrete trigger is still a finding, even if a linter would also
  flag it.
- In intent review only: style, naming, formatting and maintainability. These
  belong to the task reviewer's quality verdict.

## Finding labels

- The task reviewer sets `checked_against: SC-n | none` on each finding.
- In intent review, the required quote of the verbatim intent sentence is the label.
