---
name: tickets
description: "Turn a brief (brief.md, prd.md, intent.md, notes) into a milestone and GitHub issues the team can start on. Each ticket is built to pass harness:intake as READY. One owner approval for the whole batch. Use when the owner has a brief and wants tickets."
disable-model-invocation: true
argument-hint: "<brief path> [--max 30] [--milestone <name>]"
allowed-tools: Read, Glob, Grep, AskUserQuestion, Bash(gh repo view *), Bash(gh label list *), Bash(gh label create *), Bash(gh issue list *), Bash(gh issue create *), Bash(gh api repos/*/milestones*)
---

# Tickets: brief to GitHub issues

Goal: every ticket passes `harness:intake` as READY.

## 1. Read

- Read the brief; read `## Intent` verbatim and never edit it.
- Read the repo: `gh label list`, open milestones, open issues (`gh issue list --state open`).
- Read the code areas the brief names, to split by area and write a real `Verify:` command.

## 2. Is the brief ready?

| Check | If no |
|---|---|
| The goal fits one sentence | Ask |
| Each requirement has an observable outcome | Ask, with a drafted outcome as the recommended answer |
| Scope and out-of-scope are clear | Ask |
| No decision is left that belongs to the owner (auth, data deletion, public contract, money, external provider) | Ask |

- Look up facts yourself. Ask the owner only for decisions.
- Ask all questions in ONE AskUserQuestion round, max 4, each with a recommended answer.
- If more than 4 decisions are open, stop. Say the brief is not ready and list them.

## 3. Split

Read `references/process.md` section 3 (Split) before you split. Split by outcome: one ticket = one PR = one thing a reviewer can check. More than `--max` (default 30) tickets: stop.

## 4. Ticket types

| Type | When | Label | Template |
|---|---|---|---|
| feature | New or changed behavior | `enhancement` | `references/feature.md` |
| bug | Wrong behavior today | `bug` | `references/bug.md` |
| docs | Only docs, README, ADR, CHANGELOG change | `documentation` | `references/docs.md` |

Every ticket gets: title `[P1|P2] <verb> <one thing>`, a type label, `size:S|M|L`, `area:<name>`.
Every template ends with:

    Verify: <command> exits <code> and prints <exact text or count>
    Deps: #<n> | none
    source: <brief path>#<section>

## 5. Self-check each ticket (the intake READY test)

Run the intake READY test in `references/process.md` section 5 on each ticket and rewrite until every item is yes.

## 6. Duplicates

Check duplicates as `references/process.md` section 6 says. Same `source:` means skip; same goal from another source means `overlap`.

## 7. Labels and milestone

See `references/process.md` section 7.

## 8. Approval (one question)

Show one table: #, type, title, size, priority, deps, `Verify:`, status (`new` / `exists #n` / `overlap #n`).
Below it: counts to create and skip, new labels, milestone.

Ask ONE question. The "go" option names the exact count, for example "Create 12 issues".
For each `overlap`, ask in the same round: create anyway or skip.

## 9. Create

Order: labels, milestone, then tickets in dependency order, then the epic last.

- Replace each draft dep (`T3`) with the real issue number.
- Epic: only if 2 or more tickets. Title `[Epic] <goal>`. Body: the goal, then a checklist `- [ ] #n <title>` of every ticket.
- Stop at the first `gh` error. Do not retry. Report what was created and what was not.

## 10. Re-run

Re-running on the same brief is safe (`references/process.md` section 10). Never edit existing issues.

## 11. Report

- Created issues, skipped issues, new labels, milestone link.
- Next: `/harness:autopilot <milestone>`.
