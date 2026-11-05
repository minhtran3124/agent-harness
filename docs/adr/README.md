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
gets a table-only row and no ADR file. The script also checks what it can check exactly: it needs at least two options that are not
`n/a`, and it refuses a title that starts with `Boundary: ` or `UAT not run`. `confidence` never
decides this.

The script also reads this folder. A decision whose ticket already has an ADR here with the same
title slug or the same non-empty context and the same decision text is skipped, so a re-run writes
no duplicate. If the decision text changed, the script writes a new ADR that names the old one in
its Context and marks the old one `superseded` with `superseded_by`. Only numeric tickets are
checked this way; run-level decisions (ticket `run`) are not.

`needs_review` is a separate flag: it asks the owner to look at a decision before the merge. It
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

On 2026-10-29 the folder was pruned and renumbered 0001 to 0010: most old ADRs recorded small,
reversible choices that now live in the code, tests and PR history. An old number in a PR body or
commit no longer matches a file here. Get a pruned ADR back with
`git log --diff-filter=D -- docs/adr/NNNN-*` and `git show <sha>^:docs/adr/<file>`.

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

Older files may carry a legacy status that is none of these; a later cleanup (#566) handles them.

## How to supersede

1. Write the new ADR (it gets the next number). Name the old ADR in its Context.
2. In the old ADR, change `status` to `superseded` and add the line `superseded_by: NNNN` to the
   frontmatter. Change nothing else in the old ADR.

## How a reviewer reads them

Open the `## Decisions` section in the PR body. For each ADR read Decision, Why and How to reverse.
Reverse a decision with the stated steps, or supersede it. Open owner questions are not ADR files:
they are listed under `## Needs your decision` in the PR body.
