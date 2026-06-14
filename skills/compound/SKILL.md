---
name: compound
description: >
  Knowledge compounding skill — transforms session learnings into persistent,
  discoverable documentation. Use after any session where a bug was solved,
  a non-obvious pattern was discovered, an architectural decision was made, or
  an approach was tried and abandoned (a failure worth not repeating).
  Trigger: /compound
---

# Compound — Knowledge Compounding

Transforms session learnings into `docs/solutions/` — persistent documentation
that future agents and developers can discover and reuse.

**Announce at start:** "Compounding knowledge from this session..."

## When to Use

Run `/compound` after any session where:
- A bug was solved with a non-trivial root cause
- A non-obvious pattern or API behavior was discovered
- An architectural decision was made with considered alternatives
- An approach was tried and abandoned (the dead end is worth recording)
- A `Harness-Delta: backlog` signal was raised by a subagent

Do NOT run after every session. Only compound when something is genuinely worth
preserving for future sessions.

## Workflow

### Step 1: Launch 4 parallel research subagents

Dispatch all four concurrently using the Agent tool. Provide each with the
session context. They read the session transcript and git diff. They return
**text only** — no file writes.

Subagent prompt files are in `.claude/skills/compound/subagents/`.

The Related Docs Finder needs `module` and `tags` from the Context Analyzer to
assess overlap accurately. Choose one of these two approaches:

**Option A — 3+1 sequential (recommended for accuracy):**
1. Dispatch Context Analyzer, Solution/Pattern Extractor, Decision Extractor in parallel
2. Wait for Context Analyzer to complete and extract `module` + `tags`
3. Dispatch Related Docs Finder with those exact values

**Option B — All 4 in parallel (faster, slightly less accurate):**
Dispatch all four at once. Pass a best-guess `module` and `tags` to the Related
Docs Finder based on your own reading of the session context. The Related Docs
Finder will use these as its search terms.

| Subagent | Prompt file |
|---|---|
| Context Analyzer | `context-analyzer-prompt.md` |
| Solution/Pattern Extractor | `solution-extractor-prompt.md` |
| Decision Extractor | `decision-extractor-prompt.md` |
| Related Docs Finder | `related-docs-finder-prompt.md` |

### Step 2: Collect findings

Wait for all subagents to complete. Parse their structured text output:
- `CONTEXT_ANALYSIS` block from Context Analyzer — extract: `module`, `tags`, `category`, `slug`, `severity`, `applicable_when`
- `BUG_TRACK`, `KNOWLEDGE_TRACK`, and `FAILURE_TRACK` blocks from Solution/Pattern Extractor
- `DECISION_TRACK` block(s) from Decision Extractor — if multiple decisions were
  made, the extractor returns numbered blocks: `DECISION_TRACK_1`, `DECISION_TRACK_2`,
  etc. Collect all numbered variants present.
- `RELATED_DOCS` block from Related Docs Finder

### Step 3: Determine tracks to emit

Apply the emission rule for each track:

| Track | Required sections (all must be non-empty and not `[none]`) |
|---|---|
| **bug** | Problem, Root_Cause, Fix |
| **knowledge** | Pattern, How_to_Use |
| **decision** | Context, Options_Considered, Decision_and_Rationale |
| **failure** | Symptom, Wrong_Approach, Why_It_Failed, Correct_Approach |

Skip any track where one or more required sections are `[none]` or empty.
Do not emit an empty track.

### Step 4: Determine output paths

For each track to emit:

1. **Category**: use `category` from CONTEXT_ANALYSIS (e.g. `kb`, `streaming`)
2. **Slug**: use `slug` from CONTEXT_ANALYSIS (e.g. `voyage-rate-limit-chunking`)
3. **Base path**: `docs/solutions/[category]/[slug].md`
4. **Collision handling**:
   - Check if `docs/solutions/[category]/[slug].md` already exists
   - If YES and overlap is **High** → update existing file (add new info, don't duplicate)
   - If YES and overlap is **Moderate** or **Low** → use `[slug]-2.md` (then `-3`, etc.)
   - If NO → use `[slug].md`

### Step 5: Write output files

For each emitted track, create the directory if needed and write the file.

**Bug track:**
```markdown
---
problem_type: bug
module: [module from CONTEXT_ANALYSIS]
tags: [tags from CONTEXT_ANALYSIS]
severity: [severity from CONTEXT_ANALYSIS]
applicable_when: [applicable_when from CONTEXT_ANALYSIS]
affects:
  - [primary file from BUG_TRACK Fix section — file path only, one per line]
supersedes: null
confidence: high
confirmed_at: [today's date YYYY-MM-DD]
---
## Problem
[Problem content from BUG_TRACK]

## Root Cause
[Root_Cause content from BUG_TRACK]

## Fix
[Fix content from BUG_TRACK]

## Regression Test
[Regression_Test content from BUG_TRACK — REQUIRED; do NOT omit even when [none]]

## Code Example
[Code_Example content from BUG_TRACK — omit section if [none]]

## Prevention
[Prevention content from BUG_TRACK — omit section if [none]]

## Related
[Paths from RELATED_DOCS.existing_files — omit section if empty]
```

**Knowledge track:**
```markdown
---
problem_type: knowledge
module: [module from CONTEXT_ANALYSIS]
tags: [tags from CONTEXT_ANALYSIS]
severity: [severity from CONTEXT_ANALYSIS]
applicable_when: [Applicable_When from KNOWLEDGE_TRACK]
affects:
  - [files this pattern applies to — from KNOWLEDGE_TRACK, file path only, one per line]
supersedes: null
confidence: high
confirmed_at: [today's date YYYY-MM-DD]
---
## Applicable When
[Applicable_When content from KNOWLEDGE_TRACK]

## Pattern
[Pattern content from KNOWLEDGE_TRACK]

## How to Use
[How_to_Use content from KNOWLEDGE_TRACK]

## Code Example
[Code_Example content from KNOWLEDGE_TRACK — omit section if [none]]

## Gotchas
[Gotchas content from KNOWLEDGE_TRACK — omit section if [none]]

## Related
[Paths from RELATED_DOCS.existing_files — omit section if empty]
```

**Decision track:**
```markdown
---
problem_type: decision
module: [module from CONTEXT_ANALYSIS]
tags: [tags from CONTEXT_ANALYSIS]
severity: [severity from CONTEXT_ANALYSIS]
applicable_when: [Applicable_When from DECISION_TRACK]
affects:
  - [files impacted by this decision — from DECISION_TRACK]
supersedes: null
confidence: high
confirmed_at: [today's date YYYY-MM-DD]
---
## Applicable When
[Applicable_When content from DECISION_TRACK]

## Context
[Context content from DECISION_TRACK]

## Options Considered
[Options_Considered content from DECISION_TRACK]

## Decision & Rationale
[Decision_and_Rationale content from DECISION_TRACK]

## Consequences
[Consequences content from DECISION_TRACK — omit section if [none]]

## Related
[Paths from RELATED_DOCS.existing_files — omit section if empty]
```

If multiple DECISION_TRACK blocks exist (DECISION_TRACK_1, DECISION_TRACK_2, etc.),
write a SINGLE consolidated file: `[slug]-decisions.md`.
Do NOT write separate files per decision — decisions from the same session share
context and must be read together.

Use this template for the consolidated file:

```markdown
---
problem_type: decision
module: [module from CONTEXT_ANALYSIS]
tags: [union of tags from all DECISION_TRACK blocks + CONTEXT_ANALYSIS — deduplicated]
severity: [severity from CONTEXT_ANALYSIS]
applicable_when: [applicable_when from CONTEXT_ANALYSIS]
affects:
  - [union of affected files across all DECISION_TRACK blocks — one per line]
supersedes: null
confidence: high
confirmed_at: [today's date YYYY-MM-DD]
---

## Applicable When
[applicable_when from CONTEXT_ANALYSIS]

## Decision 1
### Context
[Context from DECISION_TRACK_1]
### Options Considered
[Options_Considered from DECISION_TRACK_1]
### Decision & Rationale
[Decision_and_Rationale from DECISION_TRACK_1]
### Applicable When
[Applicable_When from DECISION_TRACK_1]
### Consequences
[Consequences from DECISION_TRACK_1 — omit section if [none]]

## Decision 2
### Context
[Context from DECISION_TRACK_2]
### Options Considered
[Options_Considered from DECISION_TRACK_2]
### Decision & Rationale
[Decision_and_Rationale from DECISION_TRACK_2]
### Applicable When
[Applicable_When from DECISION_TRACK_2]
### Consequences
[Consequences from DECISION_TRACK_2 — omit section if [none]]

(Repeat ## Decision N pattern for each additional DECISION_TRACK_N block.)

## Related
[Paths from RELATED_DOCS.existing_files — omit section if empty]
```

If only one DECISION_TRACK block exists, use the single-decision template defined in
Steps 1–5 of this task (same frontmatter structure + body starting with ## Applicable When,
no `-decisions` suffix on the filename).

**Failure track:**
```markdown
---
problem_type: failure
module: [module from CONTEXT_ANALYSIS]
tags: [tags from CONTEXT_ANALYSIS]
severity: [severity from CONTEXT_ANALYSIS]
applicable_when: [Applicable_When from FAILURE_TRACK]
affects:
  - [files named in FAILURE_TRACK Correct_Approach (where the working code landed) — file path only, one per line]
supersedes: null
confidence: high
confirmed_at: [today's date YYYY-MM-DD]
---
## Applicable When
[Applicable_When content from FAILURE_TRACK]

## Symptom
[Symptom content from FAILURE_TRACK]

## Wrong Approach
[Wrong_Approach content from FAILURE_TRACK]

## Why It Failed
[Why_It_Failed content from FAILURE_TRACK]

## Correct Approach
[Correct_Approach content from FAILURE_TRACK]

## Guardrail
[Guardrail content from FAILURE_TRACK — a buildable artifact tagged `existing:` or `proposed:`]

## Related
[Paths from RELATED_DOCS.existing_files — omit section if empty]
```

**Ratchet backlog (failure track only).** After writing a failure doc whose `Guardrail` is tagged
`proposed:`, append one row to `docs/harness-experimental/improvement-backlog.md` (create from the
header below if missing) so the proposed guardrail is triageable — this closes the loop from
"documented learning" to "mechanically enforced rule" (OpenAI's ratchet principle). Skip for
`existing:` guardrails (already enforced). Header if creating the file:

```markdown
# Improvement Backlog

Proposed mechanical guardrails mined from `/compound` failure tracks. Each row is a ratchet
candidate: a hook/test/lint/rule to build so a known mistake cannot recur. Triage and check off.

| Date | From failure (slug) | Proposed guardrail | Target path | Status |
|---|---|---|---|---|
```

Row shape: `| YYYY-MM-DD | <slug> | <proposed: text> | <target path> | open |`.

**Collision handling for consolidated files:**
Apply the same Step 4 rules to `[slug]-decisions.md`:
- File already exists AND overlap is **High** → update existing file (add new decision sections, don't duplicate)
- File already exists AND overlap is **Moderate** or **Low** → use `[slug]-decisions-2.md`
- File does not exist → use `[slug]-decisions.md`

### Step 5.5: Critical promotion

Check `severity` from CONTEXT_ANALYSIS.

**If `severity = standard`:** skip this step entirely.

**If `severity = critical`:** promote a summary to `docs/solutions/critical-patterns.md`.

1. If `docs/solutions/` directory does not exist, create it first.

2. Check if `docs/solutions/critical-patterns.md` exists.
   - If NO: create it with this header:
     ```markdown
     # Critical Patterns

     Promoted learnings that cost the most to discover and save the most by knowing.
     Read this file at the start of every planning session.
     Items here met all three criteria: affects multiple features, would waste ≥30 min if unknown, generalizable.

     ---
     ```

3. Append one entry per emitted track (bug / knowledge / decision / failure):
   ```markdown
   ## [YYYY-MM-DD] <slug from CONTEXT_ANALYSIS>
   **Type:** [bug | knowledge | decision | failure]
   **Module:** [module from CONTEXT_ANALYSIS]
   **Tags:** [tags from CONTEXT_ANALYSIS]
   **Applicable when:** [applicable_when from CONTEXT_ANALYSIS]

   [2-3 sentence summary. For bug: what broke and the root cause. For knowledge: what the pattern is and why it matters. For decision: what was chosen and why. For failure: what was tried, why it failed, and the correct path.]

   **Full doc:** docs/solutions/[category]/[slug].md
   ---
   ```

4. Do NOT truncate existing entries. Always append at the end of the file.

### Step 5.75: Rebuild INDEX.md

Rebuild `docs/solutions/INDEX.md` from scratch after every /compound run.
This gives future agents a single entry point into the knowledge base.
Note: failure-track files are automatically included — the scan covers all `.md` files and the Type column renders `failure` from their `problem_type` frontmatter field.

1. If `docs/solutions/` does not exist, skip this step entirely.

2. Scan all `.md` files under `docs/solutions/` recursively.
   Exclude two files: `INDEX.md` itself and `critical-patterns.md`.

3. For each file found, read its YAML frontmatter and extract:
   `problem_type`, `module`, `tags`, `severity`, `applicable_when`, `confirmed_at`.
   Parse the category from the first path segment after `docs/solutions/`
   (e.g. `docs/solutions/kb/voyage.md` → category `kb`).

4. Group files by category. Within each category, sort by `confirmed_at` descending
   (most recent first).

5. Write `docs/solutions/INDEX.md` (overwrite entirely):

   ```markdown
   # Knowledge Base Index
   > Auto-generated by /compound — do not edit manually.
   > Last updated: [today's date YYYY-MM-DD] | [N total entries]

   ## [category-1]
   | File | Type | Severity | Tags | Applicable When |
   |---|---|---|---|---|
   | [slug](category-1/slug.md) | [problem_type] | [severity] | [tags] | [applicable_when] |

   ## [category-2]
   | File | Type | Severity | Tags | Applicable When |
   |---|---|---|---|---|
   | [slug](category-2/slug.md) | [problem_type] | [severity] | [tags] | [applicable_when] |
   ```

   Rules for table content:
   - File column: markdown link `[slug](relative-path.md)` — relative path from `docs/solutions/`, use filename without extension as link text
   - Type column: value of `problem_type` frontmatter field (e.g. `bug`, `knowledge`, `decision`, `failure`)
   - Tags column: comma-separated, no brackets
   - Applicable When column: exact value from frontmatter — do not truncate
   - If a frontmatter field is missing or the file has no YAML frontmatter, write `—` in that cell
   - **All values are read from each file's written frontmatter — not from session context.** Bug track files already have `applicable_when` in their frontmatter from Step 5.
   - N in the header = total count of data rows across all category tables

6. If zero data files exist after exclusions (docs/solutions/ is empty or only contains INDEX.md and critical-patterns.md): write INDEX.md with the header and `0 entries` but no category sections.

7. Do NOT include `critical-patterns.md` or `INDEX.md` rows in the table.

### Step 6: Discoverability check

Run two separate Grep searches on `CLAUDE.md` and all files under `.claude/rules/`:
1. Pattern `docs/solutions` — checks if knowledge base is referenced
2. Pattern `critical-patterns` — checks if the flywheel file is referenced

If EITHER search returns no matches, treat the file as not yet referencing the knowledge base.

**If NOT found:** propose this exact addition to the developer:

> The knowledge base at `docs/solutions/` is not yet referenced in CLAUDE.md.
> Add this section so future agents discover it automatically?
>
> ```markdown
> ## Knowledge Base
> Solved problems, patterns, and architectural decisions: `docs/solutions/`
> Browse the index: `docs/solutions/INDEX.md`
> Critical learnings (read at planning time): `docs/solutions/critical-patterns.md`
> ```
>
> Add to CLAUDE.md? (yes/no)

**Do not auto-write.** Wait for developer approval before making any change to CLAUDE.md.

### Step 7: Print completion report

```
★ Compounded
  → docs/solutions/[category]/[slug].md         [bug]
  → docs/solutions/[category]/[slug].md         [decision]
  → docs/solutions/[category]/[slug].md         [failure]
  ↑ docs/solutions/critical-patterns.md         [promoted — critical]
  ~ docs/solutions/INDEX.md                     [rebuilt — N entries]
  CLAUDE.md surfaces docs/solutions/ ✓
```

If CLAUDE.md addition was proposed but not yet approved:
```
★ Compounded
  → docs/solutions/[category]/[slug].md         [knowledge]
  ~ docs/solutions/INDEX.md                     [rebuilt — N entries]
  CLAUDE.md: addition proposed — pending your approval
```

Note on ~ line:
- Step 5.75 runs unconditionally after Step 5.5 — INDEX.md is always rebuilt.
- The ~ line therefore always appears in the report.
- Exception: if Step 5.75 was skipped (docs/solutions/ did not exist), omit the ~ line.

If no tracks were emitted (all required sections were empty):
```
★ Nothing to compound — no complete bug fix, pattern, decision, or failure found in this session.
```

## Key Constraints

- Subagents return **text data only** — orchestrator writes ALL files
- **Never auto-write** to CLAUDE.md — always propose and ask
- **Never run automatically** — only on explicit `/compound` trigger
- Track emission is **conservative** — skip tracks with any empty required section
- One doc per track per session (except multiple DECISION_TRACKs from Decision Extractor)
