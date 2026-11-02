---
name: recall
description: Search docs/solutions/ for records that match a task before work starts. Use when you begin a task and want past failures, bugs and decisions listed first. Manual only, read-only.
argument-hint: [task description]
disable-model-invocation: true
context: fork
agent: Explore
background: false
allowed-tools: Read, Grep, Glob
---

# Recall

Find records in `docs/solutions/` that apply to this task: `$ARGUMENTS`

Read only. Never write, edit or run a command.

## Steps

1. Read `docs/solutions/INDEX.md`. Its columns are File, Type, Severity, Tags, Applicable When.
2. Read `docs/solutions/critical-patterns.md`.
3. Match the task text against Applicable When, the module (from `critical-patterns.md` and the record frontmatter) and Tags. Match on the symptom, not on the record title.
4. Open at most 3 matching records. Read each one before you list it.
5. For each opened record, check its `affects` paths with Glob or Grep, and compare its premise with the repo. Compare `confirmed_at` with today's date.

## Output

Write for this task, not about the records. Print these parts in this order. Keep the headings in English.

1. `Verdict:` the first line, one line only: known risk, reusable pattern, existing decision, or `no match`.
2. **Do first.** At most 3 actions, from `knowledge` records. Each action gives the record path, its `confirmed_at`, and the command when the record has one. Use the Correct Approach, Pattern, How to Use and Guardrail sections.
3. **Avoid.** At most 3 items, from `failure` and `bug` records. Each item gives the consequence.
4. **Check before done.** At most 3 checks, from Regression Test, Guardrail and Gotchas.
5. **Already decided.** One line per `decision` record.
6. **Possibly stale.** A record is stale if its `confirmed_at` is more than 30 days old, or if an `affects` path is missing or its premise does not match the repo. Give the reason in one line. A stale record appears only here, never in Do first, Avoid or Check before done.
7. **Search surface:** every file you read, on one line.

Leave out a part that has no item, except Verdict and Search surface.

If no record matches, print only `no match` and the `Search surface:` line.

## Absence claims

State `no match` only together with the search surface. A record you did not read is unknown, not absent (`rules/behavior.md` section 1).
