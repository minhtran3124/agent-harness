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
5. For each opened record, check its `affects` paths with Glob or Grep. A file can have moved, so search for its name under `plugins/harness/` before you call the path missing.
6. Decide for each opened record if it is out of date. It is out of date when any of these holds:
   - the record says it is superseded;
   - a command or file that its advice needs does not exist in the repo.
   A missing `affects` path alone does not make a record out of date: the advice can still hold. Note the missing path in Possibly stale.
   Also note its age: compare `confirmed_at` with today's date from the session context.

## Output

Write for this task, not about the records. Print these parts in this order. Keep the headings in English.

1. `Verdict:` the first line, one line only: known risk, reusable pattern, existing decision, `out-of-date match` (every matching record is out of date), or `no match` (no record matches).
2. **Do first.** At most 3 actions, from `knowledge` records and from the Fix of `bug` records. Each action gives the record path, its `confirmed_at`, and the command when the record has one. Use the Correct Approach, Pattern, How to Use, Fix and Guardrail sections.
3. **Avoid.** At most 3 items, from `failure` and `bug` records. Each item gives the consequence.
4. **Check before done.** At most 3 checks, from Regression Test, Guardrail and Gotchas.
5. **Already decided.** One line per `decision` record.
6. **Possibly stale.** List every record that is out of date, and every record that is more than 30 days old. Give the reason in one line.
7. **Search surface:** every file you read, on one line.

Print nothing outside these parts. List only a record you opened. If a part has more than 3 items, keep the 3 that matter most for this task.

An out-of-date record appears only in Possibly stale, never in parts 2 to 5. A record that is only old, with its paths and commands intact, may stay in parts 2 to 5 and is also listed in Possibly stale for its age.

Do not print a heading, a note or `None` for a part that has no item. Verdict and Search surface always print.

If no record matches, print `Verdict: no match` and the `Search surface:` line, and nothing else.

## Absence claims

State `no match` only together with the search surface. A record you did not read is unknown, not absent (`rules/behavior.md` section 1).
