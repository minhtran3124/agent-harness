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
inputs. A spec number labelled `prediction → measured` (a `prediction` kept beside its
`measured <YYYY-MM-DD> <source>` value) is a learning source: the gap between the two is evidence
about how the team estimates.

## Write canonical records

Read the selected `templates/` file before writing. Use the context category/slug under
`docs/solutions/<category>/`; on a high-overlap collision update the existing record, otherwise
allocate the next numeric suffix. Multiple decisions use one `-decisions` consolidated template.

Read and apply `skills/asd-ste100/SKILL.md` in STE-flavored mode to each new record. Do not change fenced
code. Do not change a literal string that a test or hook matches.

For a critical context, append an entry per emitted track to `critical-patterns.md` using its
templates. For a failure with `proposed:` guardrail, append one open row to
`docs/harness-experimental/improvement-backlog.md`; do not duplicate an `existing:` guardrail.

## Mistake twice

A learning that matches an existing record at `high` overlap is a second occurrence. Update that
record as above, then promote it: the promotion is this run's output. Update the matching
`critical-patterns.md` entry, or add one if it has none, instead of the append above; never add a
near-duplicate. Add a `**Recurred:** <date>` line under its **Full doc** line. When the learning applies only to certain
paths, also propose a path-scoped rule in the report. Do not write it: adding `paths:` to `rules/`
changes what loads, so a human decides. `moderate` overlap is not a recurrence.

Run the authority at the end of every run, even when nothing was written:

```bash
python3 scripts/rebuild_solution_index.py
```

Do not manually scan/sort/render `INDEX.md`. It excludes INDEX/critical patterns, preserves exact
frontmatter values, and offers `--check`/`--dry-run` for review.

Finally verify knowledge-base discoverability in `CLAUDE.md` and rules. If missing, propose—not
silently add—the documented knowledge-base section. Report tracks emitted, collisions, index result,
promotions (critical or recurrence), and any proposed ratchet or path-scoped rule.
