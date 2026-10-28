---
name: compound
description: Preserve durable bugs, patterns, decisions, and failed approaches as discoverable `docs/solutions/` records. Use only after a session produced a reusable learning.
allowed-tools: Read, Write, Grep, Glob, Agent, Task, Bash(python3 *)
---

# Compound — durable session knowledge

Use this skill when a non-obvious bug, reusable pattern, considered decision, or useful failure
is worth preserving. Do not emit a document merely because a
session ended.

## Extract and select

You hold the session. Run the context-analyzer, solution-extractor, and decision-extractor passes
yourself. Use the prompt files in `subagents/` as their output schemas. Then run the related-docs
pass with the context analyzer's module/tags. Dispatch a subagent only for a `docs/solutions/` tree
too large to screen from `INDEX.md`. When you dispatch one, paste in its inputs, because a fresh
context cannot see this session.

Emit only complete tracks:

| Track | Required content |
| --- | --- |
| bug | problem, root cause, fix |
| knowledge | pattern, how to use |
| decision | context, options, rationale |
| failure | symptom, wrong approach, why it failed, correct approach |

For the bug track, when `specs/<slug>/diagnosis.md` exists, take the root cause from its
`Confirmed:` hypothesis.

Skip incomplete or `[none]` tracks. Preserve a relevant active spec’s alternatives as decision
inputs. A spec number labelled `prediction → measured` (a `prediction` kept beside its
`measured <YYYY-MM-DD> <source>` value) is a learning source. The gap between the two is evidence
about how the team estimates.

## Write canonical records

Read the selected `templates/` file before writing. Use the context category/slug under
`docs/solutions/<category>/`. On a high-overlap collision, update the existing record. Otherwise,
allocate the next numeric suffix. Multiple decisions use one `-decisions` consolidated template.

Read and apply `${CLAUDE_PLUGIN_ROOT}/skills/asd-ste100/SKILL.md` in STE-flavored mode to each new record. Do not change fenced
code. Do not change a literal string that a test or hook matches.

For a critical context, append an entry per emitted track to `critical-patterns.md` using its
templates. Name a failure's `proposed:` guardrail in the report as a proposed ratchet. Do not build it.

## Mistake twice

A learning that matches an existing record at `high` overlap is a second occurrence. Update that
record as above, then promote it. The promotion is this run's output. Update the matching
`critical-patterns.md` entry, or add one if it has none. Do this instead of the append above.
Never add a near-duplicate. Add a `**Recurred:** <date>` line under its **Full doc** line. When the
learning applies only to certain paths, also propose a path-scoped rule in the report. Do not
write that rule. Adding `paths:` to `rules/` changes what loads, so a human decides. `moderate`
overlap is not a recurrence.

Run the authority at the end of every run, even when the run wrote nothing:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rebuild_solution_index.py
```

Do not manually scan/sort/render `INDEX.md`. It excludes INDEX/critical patterns, preserves exact
frontmatter values, and offers `--check`/`--dry-run` for review.
`applicable_when` is required in every solution file. Run `python3 plugins/harness/scripts/rebuild_solution_index.py --check`
and, in the harness repo, `python3 scripts/check_frontmatter_contract.py` before you finish. Details are in `docs/solutions/README.md`.

Finally, verify that `CLAUDE.md` and rules make the knowledge base discoverable. If they do not,
propose the documented knowledge-base section. Do not add it silently. Report the tracks emitted,
collisions, the index result, promotions (critical or recurrence), and any proposed ratchet or
path-scoped rule.
