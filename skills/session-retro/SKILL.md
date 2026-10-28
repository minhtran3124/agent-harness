---
name: session-retro
description: Retrospective on one session's record — traces where the agent struggled to a missing or misplaced piece of the repo environment (check, pointer, rule, tool, access) and proposes ranked fixes for the user to approve. Use when the user asks for a retro or post-mortem of a session that had visible friction.
disable-model-invocation: true
allowed-tools: Read, Grep, Glob, Bash(git log *), Bash(git diff *)
---

# Session Retro — change the environment, not the code

If nothing struggled, say so and stop. Rules manufactured from a clean run make the harness worse.

## The record

Default to the current session. For a past one, the transcript is
`~/.claude/projects/<project-slug>/<session-id>.jsonl`. If earlier turns were compacted, say
so: a summarized stretch cannot evidence a moment, so its lack of struggles is unknown.

## From struggle to lever

List the moments of friction, each with a pointer to where it happened. Every candidate traces
to one. The class of each decides the lever:

| Struggle | Lever |
| --- | --- |
| Slow to find a file or fact | Navigation pointer from a file the agent already reads |
| Mistake a tool could catch | Deterministic check: test, lint, hook, or CI job |
| Judgement-call mistake the reviewer missed | A rule in `rules/`, path-scoped where possible |
| Always-on steering file large or noisy | Move content to a check or a scoped rule. Delete no-op lines |
| Expensive or noisy tool call | Streamline or replace the tool or script |
| Missing information | Widen access (log to a file, expose state) |

Prefer a check whenever the violation is mechanical: a check can fail, a sentence cannot. Prose
is for real judgement calls only. A rule without `paths:` frontmatter loads every session, so
adding one is a cost to everyone. If a mistake class has no hook, test, or CI job at all, report
the missing guardrail as its own finding.

Before proposing, filter for recurrence: would this fix have helped most recent sessions, or
only this one? Look in `docs/solutions/INDEX.md`, `docs/harness-experimental/improvement-backlog.md`,
and `rules/`. A recorded match is evidence of recurrence — cite it and raise its priority rather
than duplicating it. An existing guard that should have fired turns the finding into "why did it
not fire?". A one-off with no prior record is reported as one.

## Report

Rank by expected recurrence times the cost each recurrence carries. Per candidate give the
struggle with its pointer, the class, the proposed lever, the target path, its ongoing cost, and
the evidence tier it would reach (traceability, provenance, or truth). List steering lines that
look dead separately, flagged for review. Name the limits that apply to this run. (One session cannot
show an older rule is obsolete. Its topic may be overweighted.)

Then stop. Nothing changes until the user picks candidates. Approved mechanical items become
`improvement-backlog.md` rows or a `intake` task. Durable knowledge goes through
`compound`.

Verifies: each candidate cites a moment in the session record and a classified lever.
Does not verify: that the struggle would recur, or that the proposed fix prevents it.
