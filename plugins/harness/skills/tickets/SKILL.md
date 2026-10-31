---
name: tickets
description: "Turn a brief (brief.md, prd.md, intent.md, notes) into a milestone and GitHub issues, each built to pass harness:intake as READY, after one owner approval. Use when the owner has a brief and wants tickets."
disable-model-invocation: true
argument-hint: "<brief path> [--max 30] [--milestone <name>]"
allowed-tools: Read, Glob, Grep, AskUserQuestion, Bash(gh repo view *), Bash(gh label list *), Bash(gh label create *), Bash(gh issue list *), Bash(gh issue create *), Bash(gh api repos/*/milestones*)
---

# Tickets: brief to GitHub issues

Goal: every ticket you create passes `harness:intake` as READY, so `/harness:autopilot` can start it with no new question.

## NEVER

- Never write a `Decide:` ticket. Intake does not pass a ticket with an open owner decision, and it has no real `Verify:` command.
- Never put the epic in the milestone. Autopilot reads every open issue there, and an epic has no `Verify:` row.
- Never create anything before step 8. `gh issue create` is pre-allowed, so that approval is the only control.
- Never edit an existing issue or the brief's `## Intent`. The owner owns both.
- Never write "works", "correctly", "as expected" or "properly" in `Verify:`. Such a row cannot fail.

## 1. Read

**Required: Read `references/process.md` now.**

- Read the brief, the code it names (for a real `Verify:` command), `gh label list --limit 1000`, and (unquoted) `gh api repos/{owner}/{repo}/milestones -X GET -f state=all --paginate`.
- Read every issue with the Duplicates command.

## 2. Is the brief ready?

Ask if: the goal needs more than one sentence; a requirement has no observable outcome; scope is unclear; an owner decision is open (auth, data deletion, public contract, money, provider).

- Look up facts yourself. Ask the owner only for decisions.
- Ask in ONE AskUserQuestion round, max 4, each with a recommended answer. Write each answer into the tickets.
- More than 4 open decisions: stop, say the brief is not ready, list them.

## 3. Split

Apply that `process.md` section.

## 4. Ticket types

| Type | When | Label | Template |
|---|---|---|---|
| feature | New or changed behavior | `enhancement` | `references/feature.md` |
| bug | Wrong behavior today | `bug` | `references/bug.md` |
| docs | Only docs change | `documentation` | `references/docs.md` |

Each ticket: title `[P1|P2] <verb> <one thing>`, type label, `size:S|M|L`, `area:<name>`. Every template ends with:

    Verify: <command> exits <code> and prints <exact text or count>
    Deps: #<n>[, #<m>] | none
    source: <brief path>#<section>/<slug>

## 5-7. Self-check, duplicates, labels

Apply those `process.md` sections.

## 8. Approval

Show one table: #, type, title, size, priority, deps, `Verify:`, status (`new` / `exists #n` / `overlap #n` / `wait #n`); then counts, new labels, close label names, milestone.

Ask one AskUserQuestion. Put the counts, the milestone and each overlap in the question text, because the dialog can hide the table. The "go" option names the exact count, e.g. "Create 12 issues".

If overlaps exist, apply the Overlaps section of `references/process.md`.

## 9. Create

Order: labels, milestone (`gh api repos/{owner}/{repo}/milestones -f title=<name>`), tickets by dependency, epic last.

- Pass each body on stdin: `gh issue create ... --body-file - <<'EOF'`. A multi-line `--body` is denied, and this skill has no Write tool.
- Replace each draft dep (`T3`) with its issue number. A skipped ticket's dep: see Deps.
- Epic: apply the Epic section of `references/process.md`.
- On the first `gh` error stop, no retry; report what exists.

## 10. Re-run

Apply that `process.md` section.

## 11. Report

Created and skipped issues, new labels, milestone, and anything process.md says to list. Next: `/harness:autopilot <milestone>`.
