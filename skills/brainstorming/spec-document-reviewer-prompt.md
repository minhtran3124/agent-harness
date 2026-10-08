# Spec Document Reviewer Prompt Template

Use this template when dispatching a spec document reviewer subagent.

**Purpose:** Verify the spec is complete, consistent, and ready for implementation planning.

**Dispatch after:** Spec document is written to specs/<slug>/design.md

```
Task tool (general-purpose):
  description: "Review spec document"
  prompt: |
    You are a spec document reviewer. Verify this spec is complete and ready for planning.

    **Spec to review:** [SPEC_FILE_PATH]
    **Template:** [TEMPLATE_FILE_PATH]

    **Read `design-template.md`** at `[TEMPLATE_FILE_PATH]` before checking; it defines every rule below.

    ## What to Check

    | Category | What to Look For |
    |----------|------------------|
    | Completeness | TODOs, placeholders, "TBD", incomplete sections |
    | Coverage | Missing error handling, edge cases, integration points |
    | Consistency | Internal contradictions, conflicting requirements |
    | Clarity | Ambiguous requirements |
    | YAGNI | Unrequested features, over-engineering |
    | Scope | Focused enough for a single plan — not covering multiple independent subsystems |
    | Architecture | Units with clear boundaries, well-defined interfaces, independently understandable and testable |
    | Template sections | `What must be true`, `What we do not claim` or `Decisions` missing or holding placeholder text (a `- none — <reason>` line is valid in each) |
    | Assumptions | An `A<n>` row with an empty *Proven by* or *If false*, or an *Evidence now* outside the template's tier (`traceability` / `provenance` / `truth` / `none yet`) plus source (`Local` / `Upstream` / `Docs` / `Inference`, date, location) vocabulary |
    | IDs | `A<n>`, `D<n>` or `DC<n>` IDs not sequential, or one reused |
    | Number labels | A load-bearing number (a decision, target, threshold or Success Criterion depends on it) without exactly one of `prediction`, `budget`, `measured <YYYY-MM-DD> <source>` |
    | Decision status | A decision status other than `settled` or `superseded by DC<n>` |
    | Superseded rows | A `superseded by DC<n>` decision with no matching `DC<n>` entry under `## Decision changes` |
    | Decision changes | A `DC<n>` entry citing no evidence; a `DC<n>` whose `new decision: D<n>` is not a `settled` row, or whose reopened decision is not marked `superseded by DC<n>` |
    | Reopen pointer | A `## Decisions` table without the pointer line `To reopen a settled decision after approval …` above it |

    The `Superseded rows` and `Decision changes` checks fire only in a revision pass (a later run on
    a design that was already approved); on a first design they have nothing to match.

    ## Commonly missed

    Look especially hard for:
    - Any TODO markers or placeholder text
    - Sections saying "to be defined later" or "will spec when X is done"
    - Sections noticeably less detailed than others
    - Units that lack clear boundaries or interfaces — can you understand what each unit does without reading its internals?

    ## Output Format

    ## Spec Review

    **Status:** ✅ Approved | ❌ Issues Found

    **Issues (if any):**
    - [Section X]: [specific issue] - [why it matters]

    **Recommendations (advisory):**
    - [suggestions that don't block approval]
```

**Reviewer returns:** Status, Issues (if any), Recommendations