---
name: create-pr
description: Generates a PR description template — title, summary, tasks, file changes, and notes. Use when the user asks to write a PR description, create a PR template, or prepare a pull request write-up. Does NOT push code or create a real PR on GitHub.
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
- Group changed files by module/area
- Focus on what changed and why — not how

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

[1–3 sentences. What problem does this solve or what does it add? Focus on the "why".]

## Tasks

- [What was done — one clear line per task]
- [Keep it short; no implementation details]

## File Changes

| File | Type | What changed |
|------|------|--------------|
| `path/to/file.py` | Modified | One-line description |
| `path/to/new_file.py` | Added | What this file does |
| `path/to/removed.py` | Deleted | Why it was removed |

## Notes

[Optional. Caveats, follow-ups, known limitations, or anything reviewers should know. Remove if nothing notable.]
```

---

## Rules

| Section | Rule |
|---------|------|
| **Title** | `type: description`, max 72 chars |
| **Summary** | Why, not how. 1–3 sentences max. |
| **Tasks** | One bullet per task. Clear and direct. No over-explaining. |
| **File Changes** | One row per file. One sentence. Group by dir if 10+ files. |
| **Notes** | Only include if genuinely useful to reviewers. |

**Change type labels:** `Added` · `Modified` · `Deleted` · `Renamed` · `Refactored`

**Do not** include line-by-line code explanations anywhere in the description.
