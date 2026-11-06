---
name: compound
description: Preserve durable bugs, patterns and failed approaches as `docs/solutions/` lessons, and decisions as `docs/adr/` ADRs. Use only after a session produced a reusable learning.
allowed-tools: Read, Write, Grep, Glob, Agent, Task, Bash(python3 *)
---

# Compound — durable session knowledge

Use this skill when a non-obvious bug, reusable pattern, considered decision, or useful failure
is worth preserving.

## Extract and select

You hold the session. Run the context-analyzer, solution-extractor, and decision-extractor passes
yourself. Use the prompt files in `subagents/` as their output schemas. Then run the related-docs
pass with the context analyzer's module/tags. Dispatch a subagent only for a `docs/solutions/` tree
too large to screen from `INDEX.md`. When you dispatch one, paste in its inputs.

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
`measured <YYYY-MM-DD> <source>` value) is a learning source.

## Write canonical records

Read the selected `templates/` file before writing. Use the context category/slug under
`docs/solutions/<category>/`. On a high-overlap collision, update the existing record. Otherwise,
allocate the next numeric suffix.

The decision track is the exception: it writes `docs/adr/`, not `docs/solutions/`. Map each decision to `${CLAUDE_PLUGIN_ROOT}/skills/compound/templates/decision-consolidated.md` and run `${CLAUDE_PLUGIN_ROOT}/scripts/write_adrs.py`. The extractor returns `How_to_Reverse` and `Confidence` for each decision. Copy them as given. Set `stage` to `compound`. If `How_to_Reverse` is `[none]` or empty, use `n/a` for `how_to_reverse`. If `Confidence` is not exactly `high`, `medium` or `low`, use `low`, because `write_adrs.py` exits 2 on any other value. Never invent a value.

Pass `--table-out <file>` to `write_adrs.py`. Report `not recorded: <reason>` for each decision that wrote no file. Rules: `${CLAUDE_PLUGIN_ROOT}/skills/compound/references/not-recorded.md`.

Read and apply `${CLAUDE_PLUGIN_ROOT}/skills/asd-ste100/SKILL.md` in STE-flavored mode to each new record. Do not change fenced
code. Do not change a literal string that a test or hook matches.

For a critical context, append an entry per emitted track to `critical-patterns.md` using its
templates. A decision track has no `docs/solutions/` file: its **Full doc** link is the ADR path that `write_adrs.py` printed (`docs/adr/NNNN-*.md`). A decision with no ADR gets no link. Name a failure's `proposed:` guardrail in the report as a proposed ratchet. Do not build it.

## Mistake twice

A learning that matches an existing record at `high` overlap is a second occurrence. Update that
record as above, then promote it. The promotion is this run's output. Update the matching
`critical-patterns.md` entry, or add one if it has none. Do this instead of the append above.
Add a `**Recurred:** <date>` line under its **Full doc** line. When the
learning applies only to certain paths, also propose a path-scoped rule in the report. Do not
write that rule. A human decides. `moderate`
overlap is not a recurrence.

Run the authority at the end of every run, even when the run wrote nothing:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/rebuild_solution_index.py
```

Do not manually scan/sort/render `INDEX.md`.
`applicable_when` is required in every solution file. Before you finish, run both checks in `docs/solutions/README.md` (`## Checks`).

Finally, verify that `CLAUDE.md` and rules make the knowledge base discoverable. If they do not,
propose the documented knowledge-base section. Do not add it silently. Report the tracks emitted,
collisions, the index result, promotions (critical or recurrence), and any proposed ratchet or
path-scoped rule.
