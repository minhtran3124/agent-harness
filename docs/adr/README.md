# Architecture Decision Records

An ADR records one decision that a model made on its own during an autonomous run. A reviewer reads
the ADRs to see what was decided, why, and how to undo it, without reading the whole diff.

## Who writes them

Stage agents never write ADR files. They return `decisions[]` to the workflow (see
`skills/decision-record/SKILL.md`). A final ADR stage writes all files for the run with
`python3 scripts/write_adrs.py`. Parallel worktrees would collide on numbers, so the script is the
only writer.

## Which decisions get a file

Not every decision gets a file. `write_adrs.py` first merges duplicates (same ticket and the same
title slug or identical non-empty context; the highest `confidence` is kept (high, then medium, then low), a tie keeps the first,
`adr` and `needs_review` carry over, and `owner_confirmed` survives only if every merged item has it).
It then writes a file only for a decision with `adr: true`. A decision is `adr` only when it (a)
changes harness behavior, a data or config contract, or how users work, and (b) had at least two
viable options, listed in `options`. A scope note (Boundary) and a "UAT not run" event are never
`adr`. A decision the agent marks `dangerous` or `contradicts_confirmed` is never `adr` either: the
workflow (`takeDecisions` in `ship.js`) sets `adr` to false for it, because the part was not done.
It still shows in the PR table and under "Needs your decision" with `needs_review: true`, so it
gets a table-only row and no ADR file. The script also checks what it can check exactly: it
needs at least two options that are not `n/a`, and it refuses a title that starts with
`Boundary: ` or `UAT not run`. `confidence` never decides this.

The script also reads this folder. A decision whose ticket already has an ADR here with the same
title slug or the same non-empty context and the same decision text is skipped, so a re-run writes
no duplicate. If the decision text changed, the script writes a new ADR that names the old one in
its Context and marks the old one `superseded` with `superseded_by`. Only numeric tickets are
checked this way; run-level decisions (ticket `run`) are not.

`needs_review` is a separate flag on the decision, not a field of the ADR file: it asks the owner to look at a decision before the merge. It
does not make a file. Every merged decision, with or without a file, is one row in the `## Decisions`
table of the PR body. A row says `ADR file`, `owner-confirmed`, `already recorded (ADR NNNN)` or
`table only`.

## Design records

A design record is an ADR with `stage: design`. `brainstorming` at depth L returns the design as a
`decisions[]` entry, and the same ADR stage writes it here. A design is never written under
`specs/`, which is local scratch and is not tracked.

## Pruned records

The prune kept every record that is critical, a public contract, a safety rule or a real
trade-off, even when it was not flagged. Only a decision that passes the gate above gets a new file.

On 2026-11-05 the folder was pruned again and renumbered 0001 to 0012: most old ADRs recorded small,
reversible choices that now live in the code, tests and PR history. Old numbers in PR bodies, commits
and open PRs no longer match a file here; use the map below. An old number can now name a different
record (0003, 0004, 0005, 0006, 0007, 0008, 0009 and 0010 do), so find the old file name first:
`git log --diff-filter=D --name-only --format= -- docs/adr`. Then get it back with
`git log --diff-filter=D --format=%h -- docs/adr/<old-file>` and `git show <sha>^:docs/adr/<old-file>`.

### Migrated records 0013 to 0030

ADRs 0013 to 0030 are the 18 decisions that lived in eight `docs/solutions/` decision notes. They were
written by `write_adrs.py` with ticket `legacy`, stage `solutions-migration` and the date of the source
note. `docs/adr/` is the one store for decisions; `docs/solutions/` keeps lessons.

### Old-to-new map

Each row starts with the old number. A kept record shows its new number. A deleted record shows
where its content lives now.

| Old | New or fate |
|---|---|
| 0001 | 0001 (unchanged) |
| 0002 | 0002 (unchanged) |
| 0003 | deleted: `hooks/clean-worktrees.sh` requires state MERGED before cleanup |
| 0004 | deleted: `hooks/clean-worktrees.sh` removes only the merged PR's head branch (`headRefName` filter) |
| 0005 | 0003 |
| 0006 | 0004 |
| 0007 | 0005 |
| 0008 | deleted: serial UAT per ticket is in `workflows/ship.js` (UAT stage, "Serial over the tickets") |
| 0009 | 0006 |
| 0010 | 0007 |
| 0100 | deleted: a "UAT not run" event for #494; lives in that PR body |
| 0101 | deleted: a "UAT not run" event for #500; lives in that PR body |
| 0102 | deleted: a "UAT not run" event for #503; lives in that PR body |
| 0103 | deleted: a "UAT not run" event for #505; lives in that PR body |
| 0104 | deleted: the `Refs` keyword is in `skills/release-notes/references/fact-list-schema.md` |
| 0105 | deleted: duplicate of 0106; the rule is in `scripts/check_release_summary.py` |
| 0106 | deleted: the bare-number rule is in `scripts/check_release_summary.py` |
| 0107 | deleted: a "UAT not run" event for #514; lives in that PR body |
| 0108 | 0008 |
| 0109 | 0009 |
| 0110 | deleted: setup step 4 writes no allow rule; the choice is kept in 0010 |
| 0111 | 0010 |
| 0112 | deleted: a boundary scope note; lives in that PR body |
| 0113 | deleted: duplicate of 0109; kept in 0009 |
| 0114 | deleted: the spike result is kept in 0010 |
| 0123 | deleted: `skills/tickets/references/process.md` exists and `tests/scripts/tickets-contract.test.sh` pins it |
| 0124 | deleted: a boundary note; the skill-count assertion lives in the test script |
| 0125 | deleted: a boundary note; lives in that PR body |
| 0126 | deleted: a boundary note; lives in that PR body |
| 0127 | deleted: a boundary note; lives in that PR body |
| 0128 | deleted: the "ask only, no token hook" choice is in `hooks/merge-guard.sh`, which emits `ask` and wires no token hook |
| 0129 | 0011 |
| 0130 | 0012 |
| 0131 | deleted: the fallback was not added; `hooks/merge-guard.sh` emits `ask` only (see 0012) |
| 0132 | deleted: a "UAT not run" event for #545; lives in that PR body |
| 0133 | deleted: a boundary note; `tests/hooks/merge-guard.test.sh` covers the cases |
| 0134 | deleted: the probe result is in 0008 and 0009 (Update sections) |
| 0135 | deleted: a boundary note; lives in that PR body |

## Numbering

- File name: `NNNN-<slug>.md`. `NNNN` has 4 digits and is sequential.
- The script finds the highest existing `NNNN` in this folder and continues from the next number.
  `README.md` and `TEMPLATE.md` are not counted.
- Order inside one run: by ticket, then by stage.
- The script refuses to overwrite a file. Do not renumber an existing ADR; a prune is the only exception.

## Status values

| Status | Meaning |
|---|---|
| `accepted` | The decision stands. A new file is always born `accepted`. To change a decision, write a superseding ADR. |
| `superseded` | A later ADR replaced it. |

## How to supersede

1. Write the new ADR (it gets the next number). Name the old ADR in its Context.
2. In the old ADR, change `status` to `superseded` and add the line `superseded_by: NNNN` to the
   frontmatter. Change nothing else in the old ADR.

## How a reviewer reads them

Open the `## Decisions` section in the PR body. For each ADR read Decision, Why and How to reverse.
Reverse a decision with the stated steps, or supersede it. Open owner questions are not ADR files:
they are listed under `## Needs your decision` in the PR body.
