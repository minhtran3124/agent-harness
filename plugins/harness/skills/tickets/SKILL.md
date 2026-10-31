---
name: tickets
description: "Turn a brief into a milestone and GitHub issues, each built to pass harness:intake as READY, after one owner approval. Use when the owner has a brief and wants tickets."
disable-model-invocation: true
argument-hint: "<brief path> [--max 30] [--milestone <name>]"
allowed-tools: Read, Glob, Grep, AskUserQuestion, Bash(gh repo view *), Bash(gh label list *), Bash(gh label create *), Bash(gh issue list *), Bash(gh issue create *), Bash(gh api repos/*/milestones*)
---

# Tickets: brief to GitHub issues

## 1. Read

- Read the brief; never edit its `## Intent`.
- Read `gh label list`, open milestones and open issues, and the code the brief names (for a real `Verify:` command).

## 2. Is the brief ready?

Ask if: the goal needs more than one sentence; a requirement has no observable outcome; scope is unclear; an owner decision is open (auth, data deletion, public contract, money, provider).

- Ask all questions in ONE AskUserQuestion round, max 4, each with a recommended answer.
- More than 4 open decisions: stop, say the brief is not ready, list them.

## 3. Split

One ticket = one PR = one thing a reviewer can check. Split by outcome.

- Too big for `size:L`: split. Same files and cannot ship alone: merge.
- A no-code decision is its own ticket, `Decide: ...`.
- Over `--max` (default 30): stop, propose two milestones.
- `P1` = others depend on it or the goal fails without it; else `P2`.
- Deps: tickets in this batch or open issues only. No cycles.

## 4. Ticket types

| Type | When | Label | Template |
|---|---|---|---|
| feature | New or changed behavior | `enhancement` | `references/feature.md` |
| bug | Wrong behavior today | `bug` | `references/bug.md` |
| docs | Only docs change | `documentation` | `references/docs.md` |

Each ticket: title `[P1|P2] <verb> <one thing>`, type label, `size:S|M|L`, `area:<name>`. Every template ends with:

    Verify: <command> exits <code> and prints <exact text or count>
    Deps: #<n> | none
    source: <brief path>#<section>

## 5. Self-check each ticket (the intake READY test)

Rewrite until yes: one-sentence goal; checkable ACs; `Verify:` has a real command and an exact string, count or exit code (never "works"); Out of scope has a line; deps exist and come earlier; `source:` names a real section.

## 6. Duplicates

Run `gh issue list --state all --search` on the source line, then title words.

- Same `source:` found: skip, show `exists #n`.
- Other source, same goal: do not create; show `overlap #n`.

## 7. Labels and milestone

- Reuse a label whose name matches ignoring case, or differs by 1 or 2 characters.
- A new label only for `area:*`, `size:*`, `P1`, `P2`. Create it without asking.
- Milestone: `--milestone`, else the brief title; create if missing.

## 8. Approval (one question)

Show one table: #, type, title, size, priority, deps, `Verify:`, status (`new` / `exists #n` / `overlap #n`); then counts, new labels, milestone.

Ask ONE question; the "go" option names the exact count, e.g. "Create 12 issues". Ask create-or-skip for each `overlap` in the same round.

## 9. Create

Order: labels, milestone, tickets by dependency, epic last.

- Replace draft deps (`T3`) with issue numbers.
- Epic: only if 2 or more tickets. Title `[Epic] <goal>`. Body: the goal, then a checklist `- [ ] #n <title>` of every ticket.
- On the first `gh` error stop, no retry; report what exists.

## 10. Re-run

Safe: step 6 skips existing `source:`. New sections become new tickets. Never edit existing issues.

## 11. Report

Created and skipped issues, new labels, milestone. Next: `/harness:autopilot <milestone>`.
