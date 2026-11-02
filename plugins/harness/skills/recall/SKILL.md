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

## Output

Print these three parts, in this order.

1. **Matches.** One line per record: the record path, then one line on why it applies.
2. **Things to avoid.** Take them from the opened records whose `problem_type` is `failure` or `bug`. Write one line per item.
3. **Search surface:** one line that lists every file you read.

If no record matches, print `no match` in place of parts 1 and 2. Then still print the `Search surface:` line.

## Absence claims

State `no match` only together with the search surface. A record you did not read is unknown, not absent (`rules/behavior.md` section 1).
