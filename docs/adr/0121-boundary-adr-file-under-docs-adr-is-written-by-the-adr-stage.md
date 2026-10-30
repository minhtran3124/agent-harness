---
ticket: run
stage: intent-fix
status: needs-review
needs_review: true
confidence: high
decided_by: claude (ship workflow: intent-fix)
date: 2026-10-30
---

# 0121. Boundary: ADR file under docs/adr/ is written by the ADR stage, not the fix stage

## Context

Intent gaps 1 and 2 both ask for the ground-check dotted-symbol ADR (result table, recommendation, WARN fallback, cost trade-off, pinned tool versions, plus install requirements, headless/workflow-agent reachability and data-egress findings). The run rules say fix stages never write ADR files; one final stage writes them from decisions[]. The ticket also says the ADR is written by the ADR stage.

## Options

- Write docs/adr/NNNN-ground-check-dotted-symbol-method.md in the fix commit
- Skip and hand the content to the ADR stage via decisions[]

## Decision

Skip both findings and leave the ADR to the ADR stage. That stage must carry the runner's measured table and, for gap 2, the install, headless and egress findings (the runner records none of these, so they must be gathered by running the tools, not invented).

## Why

Writing an ADR in the fix stage contradicts the run rule. The same call was made earlier in ADR 0117.

## Consequences

The PR has no ADR until the ADR stage runs; gap 2 findings stay unrecorded unless the ADR stage or a later measuring step supplies them.

## How to reverse

Add docs/adr/NNNN-ground-check-dotted-symbol-method.md by hand with the table and findings.
