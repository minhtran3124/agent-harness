---
name: decision-record
description: Record every decision a model makes on its own during an autonomous run. Stage agents return `decisions[]`; the final ADR stage lists all of them in the PR table and writes `docs/adr/NNNN-*.md` by script only for those with impact and a real trade-off (`adr: true`). Use when a stage decides without asking a human.
allowed-tools: Read, Write, Bash, Skill
---

# Decision Record

## When to record

| Situation | Action |
|---|---|
| Reversible and inside the ticket | `adr: false`, `needs_review: false`. PR table only. |
| Restates an owner-confirmed answer | `owner_confirmed: true`. No file unless `adr: true`. |
| Changes harness behavior, a data or config contract, or how users work, and had at least two viable options | `adr: true`. Only this gets a file. |
| Affects another ticket, a public contract, stored data, security or cost, or is costly to reverse | Choose the safer option. `needs_review: true`: listed under `## Needs your decision` for the owner. No file by itself. |
| Contradicts a confirmed answer, or is dangerous | Do not do that part. `needs_review: true`, `adr: false`. |
| A scope note (title starts with `Boundary: `) or a `UAT not run` event | `needs_review: true`, `adr: false`. Never a file. |

One store per record type: decisions in `docs/adr/`, lessons in `docs/solutions/`.

## Which decisions get a file

`write_adrs.py` applies this rule; agents do not filter.

1. Merge duplicates: same ticket and (same title slug or identical non-empty context). Keep the
   item with the highest `confidence` (high, then medium, then low; a tie keeps the first); if any
   merged item has `adr` true, keep the highest-confidence `adr` true item whole. `needs_review`
   is OR-ed; `owner_confirmed` is AND-ed.
2. Write a file only if `adr: true` and `options` lists two real options.
   `adr` wins over `owner_confirmed`; `needs_review` and `confidence` never make a file.
3. Always born `accepted`. An ADR in the folder for the same numeric ticket with the same
   title slug or context makes the decision `already recorded (ADR NNNN)`: no second file.
4. Every decision is one row in the `## Decisions` PR table (`ADR file`, `owner-confirmed`,
   `already recorded (ADR NNNN)` or `table only`).

A `dangerous` or `contradicts_confirmed` decision stops the ticket and gets no file. `## Needs your decision` in the PR body lists each `needs_review` decision with its text.

## What a good ADR says

- `title`: the decision, not the topic.
- `options`: each option you weighed, including the rejected one and why.
- `why`: the evidence that made this option win.
- `how_to_reverse`: the exact undo steps.
- `confidence`: `low` for a guess.

## How an agent returns it

Return `decisions[]` in your result. Each item has `ticket`, `stage`, `title`, `context`, `options`,
`decision`, `why`, `consequences`, `how_to_reverse`, `confidence`, `needs_review`, `adr` (required; input without it exits 2), and optionally `owner_confirmed`. Never write an ADR file.

## Other places

Every decision is an entry in `specs/<slug>/decision.md`. A depth L design from `brainstorming` is a decision with `stage: design` and `adr: true`.

## The ADR stage

1. Save all `decisions[]` of the run, each with `decided_by`, as `{"run": "<slug>", "decisions": [...]}`.
2. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_adrs.py --input <file> [--dry-run] [--table-out <file>]`. Exit 2 means bad input.
3. Commit the new files in `docs/adr/` to the PR branch.
4. Build the artifact when the Artifact tool exists (`references/artifact.md`). Run `write_adrs.py --render-section <written.json> [--artifact <url>]`; put the output, then the table file, in the PR body as `## Decisions`.

## Auto mode

The ADR stage never asks the owner. After two failed runs of step 2, return `blocked`.
