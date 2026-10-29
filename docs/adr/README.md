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
`needs_review` carries over, and `owner_confirmed` survives only if every merged item has it). It
then writes a file only for a decision that has `needs_review: true`: it is critical, affects
another ticket, a public contract, stored data, security or cost, or is a trade-off that is costly
to reverse. `confidence` never decides this. Every merged
decision, with or without a file, is one row in the `## Decisions` table of the PR body. A row for
an owner-confirmed decision without a file says `owner-confirmed`.

## Design records

A design record is an ADR with `stage: design`. `brainstorming` at depth L returns the design as a
`decisions[]` entry, and the same ADR stage writes it here. A design is never written under
`specs/`, which is local scratch and is not tracked.

## Pruned records

On 2026-10-29 the folder was pruned and renumbered 0001 to 0010: most old ADRs recorded small,
reversible choices that now live in the code, tests and PR history. An old number in a PR body or
commit no longer matches a file here. Get a pruned ADR back with
`git log --diff-filter=D -- docs/adr/NNNN-*` and `git show <sha>^:docs/adr/<file>`.

## Numbering

- File name: `NNNN-<slug>.md`. `NNNN` has 4 digits and is sequential.
- The script finds the highest existing `NNNN` in this folder and continues from the next number.
  `README.md` and `TEMPLATE.md` are not counted.
- Order inside one run: `needs_review: true` first, then by ticket, then by stage.
- The script refuses to overwrite a file. Do not renumber an existing ADR; a prune is the only exception.

## Status values

| Status | Meaning |
|---|---|
| `accepted` | The decision stands. Default for `needs_review: false`. |
| `needs-review` | A human must confirm it. Set when `needs_review: true`. |
| `superseded` | A later ADR replaced it. |

## How to supersede

1. Write the new ADR (it gets the next number). Name the old ADR in its Context.
2. In the old ADR, change `status` to `superseded` and add the line `superseded_by: NNNN` to the
   frontmatter. Change nothing else in the old ADR.

## How a reviewer reads them

Open the `## Decisions` section in the PR body. It lists `needs-review` ADRs first. For each ADR
read Decision, Why and How to reverse. Confirm it (set `status: accepted`, `needs_review: false`),
reverse it with the stated steps, or supersede it.
