---
name: compound
description: Preserve durable bugs, patterns, decisions, and failed approaches as discoverable `docs/solutions/` records. Use only after a session produced a reusable learning or a proposed harness ratchet.
allowed-tools: Read, Write, Grep, Glob, Agent, Task, Bash(python3 *)
---

# Compound — durable session knowledge

Use when a non-obvious bug, reusable pattern, considered decision, useful failure, or
`Harness-Delta: backlog` signal is worth preserving. Do not emit a document merely because a
session ended.

## Extract and select

You hold the session, so run the context-analyzer, solution-extractor, and decision-extractor
passes yourself, using the prompt files in `subagents/` as their output schemas. Then run the
related-docs pass with the context analyzer's module/tags. Dispatch a subagent only for a
`docs/solutions/` tree too large to screen from `INDEX.md`, and paste in its inputs — a fresh
context cannot see this session.

Emit only complete tracks:

| Track | Required content |
| --- | --- |
| bug | problem, root cause, fix |
| knowledge | pattern, how to use |
| decision | context, options, rationale |
| failure | symptom, wrong approach, why it failed, correct approach |

Skip incomplete or `[none]` tracks. Preserve a relevant active spec’s alternatives as decision
inputs.

## Write canonical records

Read the selected `templates/` file before writing. Use the context category/slug under
`docs/solutions/<category>/`; on a high-overlap collision update the existing record, otherwise
allocate the next numeric suffix. Multiple decisions use one `-decisions` consolidated template.

For a critical context, append an entry per emitted track to `critical-patterns.md` using its
templates. For a failure with `proposed:` guardrail, append one open row to
`docs/harness-experimental/improvement-backlog.md`; do not duplicate an `existing:` guardrail.

Run the authority at the end of every run, even when nothing was written:

```bash
python3 scripts/rebuild_solution_index.py
```

Do not manually scan/sort/render `INDEX.md`. It excludes INDEX/critical patterns, preserves exact
frontmatter values, and offers `--check`/`--dry-run` for review.

Finally verify knowledge-base discoverability in `CLAUDE.md` and rules. If missing, propose—not
silently add—the documented knowledge-base section. Report tracks emitted, collisions, index result,
critical promotion, and any proposed ratchet.
