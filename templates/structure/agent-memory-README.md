# Agent Memory

Per-agent persistent memory with confidence decay. This top-level `agent-memory/` is the
**version-controlled** home; each subagent gets its own subdirectory:

```
agent-memory/
├── README.md               # this file (tracked — the shared convention)
├── <agent-name>/           # e.g., test-runner/, coding/, brainstorming/
│   └── *.md                # individual memory entries
```

> **Runtime vs tracked:** the `memory: project` agent feature reads/writes its live copy at
> `.claude/agent-memory/<agent-name>/` (gitignored, local-only). Keep anything meant to be
> shared with the team in this top-level `agent-memory/` directory.

## Entry Format

Each memory entry carries a metadata comment at the top:

```markdown
<!-- confirmed: YYYY-MM-DD | confidence: high|medium|low | review-by: YYYY-MM-DD -->

# Memory title

Body of the memory...
```

## Confidence Levels

- `high` — verified this session or last
- `medium` — 1+ month old, or inferred from evidence
- `low` — >3 months old, or uncertain — treat as hypothesis and verify before acting

## Write Protocol

- On re-verifying an entry: update `confirmed` to today, keep or raise `confidence`
- On expired `review-by`: downgrade `confidence` one tier on next read
- Never silently delete — downgrade to `low` and let the next session decide

## What NOT to Store

- Code patterns already derivable from the current codebase (grep finds them)
- Session-specific task context (belongs in `specs/STATE.md`)
- Anything documented in `CLAUDE.md` or `docs/solutions/`
