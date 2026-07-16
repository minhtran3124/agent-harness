# Plan Document Reviewer Prompt Template

Use this template when dispatching a plan document reviewer subagent.

**Purpose:** Verify the plan chunk is complete, matches the spec, and has proper task decomposition.

**Dispatch after:** Each plan chunk is written

```text
Task tool (general-purpose):
  description: "Review plan chunk N"
  prompt: |
    You are a plan document reviewer. Verify this plan chunk is complete and ready for implementation.

    **Plan chunk to review:** [PLAN_FILE_PATH] - Chunk N only
    **Spec for reference:** [SPEC_FILE_PATH]

    ## What to Check

    | Category | What to Look For |
    |----------|------------------|
    | Completeness | TODOs, placeholders, incomplete tasks, missing steps |
    | Spec Alignment | Chunk covers relevant spec requirements, no scope creep |
    | Task Decomposition | Tasks atomic, clear boundaries, steps actionable |
| Readability | Each task has a concise heading; XML tasks live in one fenced `xml` block each (no raw `<task>` tags in body text); markdown tasks are plain markdown, never fenced |
    | File Structure | Files have clear single responsibilities, split by responsibility not layer |
    | File Size | Would any new or modified file likely grow large enough to be hard to reason about as a whole? |
| Task Syntax | Either accepted syntax per `.claude/rules/plan-format.md` — a `### Task <id>` heading with `- **Files/Action/Verify/Done:**` field bullets, OR a fenced `<task id ... wave ...>` XML block — with all four fields populated in every task (one syntax per plan) |
    | Chunk Size | Each chunk under 1000 lines |

    ## CRITICAL

    Look especially hard for:
    - Any TODO markers or placeholder text
    - Steps that say "similar to X" without actual content
    - Incomplete task definitions
    - Missing verification steps or expected outputs
    - Files planned to hold multiple responsibilities or likely to grow unwieldy

    ## Output Format

    ## Plan Review - Chunk N

    **Status:** Approved | Issues Found

    **Issues (if any):**
    - [Task X, Step Y]: [specific issue] - [why it matters]

    **Recommendations (advisory):**
    - [suggestions that don't block approval]
```

**Reviewer returns:** Status, Issues (if any), Recommendations
