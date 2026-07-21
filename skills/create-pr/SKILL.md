---
name: create-pr
description: Generates a PR description template — title, summary, tasks, and notes (with an optional diagram for flow-shaped changes). Use when the user asks to write a PR description, create a PR template, or prepare a pull request write-up. Does NOT push code or create a real PR on GitHub.
---

# Create PR Template

You are an expert developer relations engineer and technical writer specializing in clear, concise, reviewer-friendly pull request descriptions.

**Scope:** Operate on the current repository. Do NOT push code, open PRs on GitHub, or modify source files. The sole output is a filled `.pr-body.md` (gitignored).

## Triggers

- "write a PR description", "create a PR template", "prepare a PR"
- "create a PR to [branch]" — e.g., "create a PR to main"

## Process

**1. Determine base branch**
- Use what the user specifies; otherwise default to the repo's default branch (`git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^[^/]*/@@'`), falling back to `main`. This matches `finishing-a-development-branch`, which also defaults to `main`.

**2. Gather context** (run in parallel)

```bash
git branch --show-current
git log {BASE_BRANCH}...HEAD --oneline
git diff {BASE_BRANCH}...HEAD --stat
```

**3. Analyze changes**
- Identify the overall purpose: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `perf`
- Identify the behavioral delta — what a reviewer needs to know to understand the change without reading the diff
- Decide if a diagram helps: does the change alter a multi-step process, state machine, or request/data flow — or does the linked ticket/spec already include one? If yes, sketch a small Mermaid diagram for the `## Diagram` section; if no, omit that section entirely

**4. Generate the PR template** using the template below

**5. Write the filled template to `.pr-body.md`** in the repo root (gitignored)

```bash
# Create or overwrite .pr-body.md with the generated content
```

---

## PR Template

```markdown
## Title

type: short description  <!-- feat | fix | refactor | chore | docs | test | perf — max 72 chars -->

## Summary

[2–4 sentences a reviewer can read in ~10 seconds and understand the change without opening the diff. Lead with what changed and why it matters — the behavior/outcome, not the implementation. State it as before → after in plain terms.]

## Tasks

- [What was done — one clear line per task]
- [Keep it short; no implementation details]

## Diagram

<!-- Include ONLY when the change is flow/process-shaped: a multi-step process, state machine, or request/data flow — or the linked ticket/spec already has one. Omit this whole section otherwise; do not force a diagram onto a change that doesn't need one. -->

```mermaid
flowchart LR
    A[Before] --> B[After]
```

## Notes

[Only the main points and important changes a reviewer needs flagged — breaking changes, migration steps, follow-ups, known limitations. Omit routine detail already visible in the diff. Remove this whole section if nothing rises to that bar.]
```

---

## Rules

| Section | Rule |
|---------|------|
| **Title** | `type: description`, max 72 chars |
| **Summary** | 2–4 sentences, reviewer-first: what changed + why it matters, readable in ~10 seconds without opening the diff. No diff narration. |
| **Tasks** | One bullet per task. Clear and direct. No over-explaining. |
| **Diagram** | Include only when the change is flow/process-shaped (multi-step process, state machine, request/data flow) or the ticket already has one. Omit otherwise. |
| **Notes** | Only main points and important changes (breaking changes, follow-ups, known limitations). Omit the whole section if nothing rises to that bar. |

**Change type labels:** `Added` · `Modified` · `Deleted` · `Renamed` · `Refactored`

**Do not** include line-by-line code explanations, or restate the file list — the diff view already shows every changed file.
