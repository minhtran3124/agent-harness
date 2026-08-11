# compound — Knowledge Compounding Skill

Transforms session learnings into persistent, discoverable documentation under `docs/solutions/`.

**Trigger:** `compound` — never runs automatically. Only invoke after sessions where a bug was solved, a non-obvious pattern was discovered, or an architectural decision was made with considered alternatives.

---

## Architecture

The skill uses an **orchestrator + 4 subagents** model. The orchestrator (`SKILL.md`) coordinates everything — subagents only read and return text, the orchestrator writes all files.

```
compound (orchestrator — SKILL.md)
├── subagents/context-analyzer-prompt.md     → classifies what happened, assigns severity
├── subagents/solution-extractor-prompt.md   → extracts bug fixes + knowledge patterns
├── subagents/decision-extractor-prompt.md   → extracts architectural decisions (ADR format)
└── subagents/related-docs-finder-prompt.md  → finds overlapping existing docs
```

**Dispatch order (Option A — recommended):**
1. Context Analyzer + Solution Extractor + Decision Extractor in parallel
2. Wait for Context Analyzer → extract `module` + `tags`
3. Dispatch Related Docs Finder with those values (more accurate overlap detection)

**Option B (faster, slightly less accurate):** dispatch all 4 in parallel with a best-guess `module` and `tags` for the Related Docs Finder.

---

## Output Overview

Each run can produce up to 4 files:

| File | When produced |
|---|---|
| `docs/solutions/[category]/[slug].md` | Bug or knowledge track (one file each) |
| `docs/solutions/[category]/[slug]-decisions.md` | Decision track (all decisions for this session) |
| `docs/solutions/critical-patterns.md` | Appended to when `severity = critical` |
| `docs/solutions/INDEX.md` | Always rebuilt from scratch after every run |

---

## Tracks

### Bug track
Captures a bug fix with a non-trivial root cause — something a future developer would waste time rediscovering.

**Required sections (all must be non-empty):** Problem, Root_Cause, Fix

### Knowledge track
Captures a reusable pattern, API behavior, or technique discovered during the session.

**Required sections (all must be non-empty):** Pattern, How_to_Use

### Decision track
Captures an architectural decision in lightweight ADR format — what was decided, what alternatives were considered, and why.

**Required sections (all must be non-empty):** Context, Options_Considered, Decision_and_Rationale

> **Emission gate:** if any required section is `[none]` or empty, the track is skipped entirely. Never emit a partial track.

---

## Multi-Decision Consolidation

When a session produces multiple `DECISION_TRACK_N` blocks, they go into **one consolidated file** — not separate `decision-1.md`, `decision-2.md` files.

- **1 decision** → `[slug].md` (standard single-decision template, no suffix)
- **2+ decisions** → `[slug]-decisions.md` (consolidated, `## Decision 1` / `## Decision 2` sections)

**Why:** Decisions from the same session are causally related. An agent reading `decision-2.md` without `decision-1.md` context loses the constraints that drove it. Consolidated files prevent this fragmentation.

---

## Severity Triage

The Context Analyzer assigns severity to the session output:

| Severity | Criteria (all three must apply) |
|---|---|
| `critical` | (1) Affects multiple features or layers, (2) Would waste ≥30 min if unknown in a future session, (3) Generalizable beyond this specific PR |
| `standard` | Anything else — valuable but narrow scope |

Severity is used in two ways:
1. Written into every emitted file's frontmatter (`severity` field)
2. Triggers `critical-patterns.md` promotion (see below)

---

## Frontmatter Schema

Every emitted file carries this frontmatter:

```yaml
---
problem_type: [bug | knowledge | decision]
module: [primary module, e.g. kb/embedding, services/ai, skills/compound]
tags: [3-6 kebab-case tags, comma-separated]
severity: [critical | standard]
applicable_when: [one sentence — the trigger for using this doc]
affects:
  - [file path, one per line]
supersedes: null
confidence: high
confirmed_at: YYYY-MM-DD
---
```

**`applicable_when` is the primary discovery field.** It completes a specific sentence form:
- Knowledge: "Use this pattern when…"
- Decision: "Make this decision when…"
- Bug: inherited from `CONTEXT_ANALYSIS` (same sentence as the session-level trigger)

This field appears as a column in `INDEX.md`, letting a future agent scan one sentence per doc to decide whether to open the full file.

---

## Collision Handling

Before writing a new file, the Related Docs Finder assesses overlap with existing docs:

| Overlap level | Rule |
|---|---|
| **High** — same module AND ≥2 matching tags | Update existing file (add new info, don't duplicate) |
| **Moderate** — same category OR ≥1 matching tag | Use `[slug]-2.md` (then `-3`, etc.) |
| **Low** — no module or tag matches | Use `[slug].md` |

The same rules apply to `[slug]-decisions.md` consolidated files.

---

## The Flywheel Files

### `critical-patterns.md`

Promoted summaries of `severity = critical` findings. Appended to after every run where any critical track is emitted.

**Read this at the start of every planning session.** Items here met all three criteria for critical severity — they affect multiple features and would waste ≥30 min if unknown.

One entry per emitted track (bug / knowledge / decision). Entries are never truncated — always append at end.

### `INDEX.md`

Full-rebuild index of all `docs/solutions/**/*.md` files. Rebuilt from scratch after every `compound` run.

**Why full rebuild (not append-only):** prevents orphaned rows when files are renamed, moved, or deleted. The docs/solutions/ directory grows to tens of files, not thousands — full scan is negligible.

Excludes `INDEX.md` itself and `critical-patterns.md` from the table rows.

Columns: File (markdown link), Type, Severity, Tags, Applicable When.
Missing frontmatter fields → `—` in that cell.

---

## Discoverability Check

At the end of every run, the orchestrator greps `CLAUDE.md` and `rules/` for both `docs/solutions` and `critical-patterns`. If either is missing, it proposes the following addition — but **never auto-writes** to `CLAUDE.md`. Always ask first.

```markdown
## Knowledge Base
Solved problems, patterns, and architectural decisions: `docs/solutions/`
Browse the index: `docs/solutions/INDEX.md`
Critical learnings (read at planning time): `docs/solutions/critical-patterns.md`
```

---

## Key Rules

1. **Never run automatically** — only on explicit `compound` trigger.
2. **Subagents return text only** — the orchestrator writes all files.
3. **Never auto-write to CLAUDE.md** — always propose and wait for approval.
4. **Track emission is conservative** — skip any track with a single empty required section.
5. **Step 5.75 (INDEX rebuild) is unconditional** — runs even if no new files were written this run. The `~` line always appears in the completion report (except if `docs/solutions/` doesn't exist).
6. **Old files without new frontmatter fields** — write `—` in INDEX.md cells for missing `severity` / `applicable_when`. Do not backfill old files.

---

## Completion Report Format

```
★ Compounded
  → docs/solutions/[category]/[slug].md               [knowledge]
  → docs/solutions/[category]/[slug]-decisions.md     [decision — N tracks consolidated]
  ↑ docs/solutions/critical-patterns.md               [promoted — critical]
  ~ docs/solutions/INDEX.md                           [rebuilt — N entries]
  CLAUDE.local.md surfaces docs/solutions/ ✓
```

If no tracks emitted:
```
★ Nothing to compound — no complete bug fix, pattern, or decision found in this session.
```
