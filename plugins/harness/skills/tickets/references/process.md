# Tickets process rules

SKILL.md requires this file. Each section belongs to the step with the same name.

## Split

Split by outcome, not by layer. One ticket = one PR = one thing a reviewer can check.

| Rule | Why |
|---|---|
| A ticket delivers a result someone can see or test (a vertical slice) | "Add DB table" alone proves nothing |
| Pick `size:S`, `size:M` or `size:L` for each ticket | Matches the repo labels |
| If a ticket is too big for `size:L`, split it | `intake` marks it BLOCKED (too large) |
| Merge two tickets that touch the same files and cannot ship alone | Avoids two PRs that conflict |
| More tickets than `--max` (default 30): stop | Propose two milestones and split the brief |

Then pick for each ticket:

- **Type**: a ticket that changes code and docs is `feature` or `bug`, not `docs`.
- **Priority**: `P1` = other tickets depend on it, or the goal fails without it. `P2` = everything else.
- **Deps**: only tickets in this batch or closed issues, because `intake` needs a dependency done or in the batch. A dep on a skipped ticket uses that ticket's `#n`. If that `#n`, or any other dep, is open and outside this milestone, do not create the ticket: show `wait #n` in the approval table and name it in the report. A ticket that depends on a `wait` ticket is also `wait`. No cycles. If there is a cycle, merge the tickets.
- **Source**: `<brief path>` is relative to the repo root, with no leading `./`, so a re-run matches. `<slug>` is a short kebab-case name of the outcome, unique across the brief. One section can give several tickets, so the section alone is not a key.

## Self-check

Rewrite a ticket until all are yes:

- [ ] The goal fits one sentence.
- [ ] Each AC is checkable by a command or a visible behavior.
- [ ] `Verify:` names a real command and an exact string, count or exit code. A row for a change also fails on the base commit today: the ship workflow blocks a row that passes there.
- [ ] Out of scope has at least one line.
- [ ] Deps exist and come earlier in the order.
- [ ] `source:` names a real section of the brief and has a unique slug.
- [ ] No owner decision is left open in the ticket.

## Duplicates

Read every issue once, in step 1, before you write slugs:

    gh issue list --state all --limit 1000 --json number,title,body,state --jq '.[] | {number, title, state, source: ((.body // "") | gsub("\r"; "") | split("\n") | map(select(startswith("source:"))))}'

Print only these fields: full bodies are too large and a tool result can cut them off. GitHub search is fuzzy and can lag, so do not use `--search` here. If the list returns 1000 issues, run it again with a higher `--limit`.

If an issue already has a `source:` line for this brief, reuse its slug for the same outcome.

| Result | Action |
|---|---|
| A body has a line that is an exact match for the ticket's `source:` line | Skip. Show it as `exists #n` |
| A body has the line `source: <brief path>#epic` | Do not create an epic |
| Different source, same goal (compare titles and goals) | Do not create. Show `overlap #n` and ask in the approval step |
| Nothing | Create |

## Overlaps

Add one multi-select question to the approval call: "Which overlaps should I create anyway?". Options: `Skip all`, then one option per overlap. More than 3 overlaps: use `Skip all` and `Create all`; the owner types numbers under Other.

The "go" count holds new tickets only, and each selected overlap adds one. Say so in the question text.

## Labels

- Reuse an existing label only when the name matches ignoring case.
- A new label only for `area:*`, `size:*`, `P1`, `P2`. Create it without asking.
- If a new `area:*` name differs from an existing label by 1 or 2 characters, show both names in the approval step as a close name. Compare `area:*` names only: `P1` and `P2`, or `size:S` and `size:M`, are different labels.
- Milestone: `--milestone`, else the brief title. Create it if missing. If the name matches a closed milestone, stop before step 8 and ask for another name: `gh issue create` cannot rely on it, and this skill never reopens one.

## Epic

- Create it only if 2 or more tickets belong to the brief and Duplicates found no epic.
- Title `[Epic] <goal>`.
- Body: the goal, a checklist `- [ ] #n <title>` of every ticket, new or `exists`, then the line `source: <brief path>#epic`.
- No milestone, type, size or priority label.

## Re-run

Running again on the same brief creates no duplicate: Duplicates skips each `source:` that exists, including the epic.

- A new outcome becomes a new ticket. If the epic already exists, name the new ticket in the report, because the epic is not edited.
- A changed outcome shows as `exists #n`. Do not edit it: list them for the owner to update by hand.
- A slug that changed between runs shows as `overlap #n`, not as a skip, so read overlaps with care.
