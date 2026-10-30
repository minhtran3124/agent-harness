# Solutions Knowledge Base

Persistent documentation of non-obvious patterns, bug fixes, and architectural decisions.

- **Written by:** `compound` after sessions with non-trivial learnings
- **Read by:** `brainstorming` (decision track only), `xia2` (all tracks via INDEX-first lookup),
  and `compound`'s related-docs lookup; the `session-knowledge.sh` SessionStart hook
  loads `critical-patterns.md` and an `INDEX.md` pointer

## Structure

```
docs/solutions/
├── README.md              # this file — schema and conventions
├── INDEX.md               # O(1) lookup of all entries
├── critical-patterns.md   # always-read high-value patterns
└── <category>/            # grouped by domain (e.g., db, auth, streaming)
    └── <slug>.md          # individual solution
```

## Categories

Pick the smallest set that covers the domain. Common examples:
- `db/` — database, migrations, transactions, query patterns
- `auth/` — authentication, authorization, session handling
- `api/` — endpoint design, contract evolution, error shapes
- `async/` — concurrency, background tasks, context propagation
- `testing/` — test patterns, mocks, fixtures
- `infra/` — deployment, environment, CI/CD

## Front-Matter Schema

Every solution file begins with:

```yaml
---
problem_type: bug | knowledge | decision | failure
module: <area of codebase>
tags: [<keyword>, <keyword>]
severity: critical | standard
applicable_when: <one sentence: when a future agent should apply this>
affects: [<file-path>, <file-path>]
supersedes: <slug-of-older-entry>   # optional
confidence: high | medium | low
confirmed_at: YYYY-MM-DD
---
```

## Body Sections (by `problem_type`)

| Type | Required sections |
|---|---|
| `bug` | Problem, Root_Cause, Fix |
| `knowledge` | Pattern, How_to_Use |
| `decision` | Context, Options_Considered, Decision_and_Rationale |
| `failure` | Symptom, Wrong_Approach, Why_It_Failed, Correct_Approach, Guardrail |

## Confidence Decay

- `high` — verified recently (<30 days)
- `medium` — 1+ month old, or inferred
- `low` — >3 months old or uncertain — treat as hypothesis; verify before acting

On re-verification, update `confirmed_at` to today and bump confidence.

## INDEX-First Lookup

Consumers read `INDEX.md` first for O(1) domain scan, then at most 3 matching entries. `critical-patterns.md` is always read regardless of domain.
