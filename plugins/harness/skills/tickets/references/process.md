# Tickets: split, self-check, duplicates, labels, re-run

Steps 3, 5, 6, 7 and 10 of `SKILL.md`, kept whole.

## 3. Split

Split by outcome, not by layer. One ticket = one PR = one thing a reviewer can check.

| Rule | Why |
|---|---|
| A ticket delivers a result someone can see or test (a vertical slice) | "Add DB table" alone proves nothing |
| Pick `size:S`, `size:M` or `size:L` for each ticket | Matches the repo labels |
| If a ticket is too big for `size:L`, split it | `intake` marks it BLOCKED (too large) |
| Merge two tickets that touch the same files and cannot ship alone | Avoids two PRs that conflict |
| A decision with no code ("decide X") is its own ticket, titled `Decide: ...` | Other tickets depend on it |
| More tickets than `--max` (default 30): stop | Propose two milestones and split the brief |

Then pick for each ticket:
- **Type**: read the matching template (below).
- **Priority**: `P1` = other tickets depend on it, or the goal fails without it. `P2` = everything else.
- **Deps**: only tickets in this batch or existing open issues. No cycles. If there is a cycle, merge the tickets or add a `Decide:` ticket.

## 5. Self-check each ticket (the intake READY test)

Rewrite a ticket until all are yes:

- [ ] The goal fits one sentence.
- [ ] Each AC is checkable by a command or a visible behavior.
- [ ] `Verify:` names a real command and an exact string, count or exit code. It never says "works", "correctly", "as expected", "properly".
- [ ] Out of scope has at least one line.
- [ ] Deps exist and come earlier in the order.
- [ ] `source:` points to a real section of the brief.

## 6. Duplicates

For each ticket, search `gh issue list --state all --search "<source line>"`, then search by title words.

| Result | Action |
|---|---|
| Same `source:` found | Skip. Show it as `exists #n` |
| Different source, same goal | Do not create. Show `overlap #n` and ask in the approval step |
| Nothing | Create |

## 7. Labels and milestone

- Reuse an existing label when the name matches, ignoring case.
- A new label only for `area:*`, `size:*`, `P1`, `P2`. Create it without asking.
- If a new name differs from an existing label by 1 or 2 characters, use the existing one.
- Milestone: `--milestone`, else the brief title. Create it if missing.

## 10. Re-run

Running again on the same brief is safe: step 6 skips tickets whose `source:` exists.
If the brief changed, new sections become new tickets. Changed sections show as `exists #n`.
Do not edit existing issues. List them for the owner to update by hand.
