---
name: decision-record
description: Record every decision a model makes on its own during an autonomous run. Stage agents return `decisions[]`; the final ADR stage lists all of them in the PR table and writes `docs/adr/NNNN-*.md` by script only for those that need a human look. Use when a stage decides without asking a human.
allowed-tools: Read, Write, Bash, Skill
---

# Decision Record

## When to record

Record a decision when you choose between options without asking a human. Ask the table first.

| Situation | Action |
|---|---|
| Reversible and inside the ticket | Decide. Record it. `needs_review: false`. It goes in the PR table, not in an ADR file. |
| Only restates an owner-confirmed answer | Record it with `owner_confirmed: true`. No ADR file, unless it also has `needs_review: true`. |
| Affects another ticket or a public contract | Choose the safer option. Record it. `needs_review: true`. |
| Contradicts a confirmed answer, or is dangerous | Do not do that part. Record why. `needs_review: true`. |

## Which decisions get a file

The script `write_adrs.py` applies this rule. Agents do not filter.

1. Merge duplicates: same ticket and (same title slug or identical non-empty context). Keep the
   lowest `confidence` (low, then medium, then high; a tie keeps the first), so a doubtful
   duplicate is never hidden. If any merged item has `needs_review`, the kept one has it too. The
   kept one is `owner_confirmed` only if every merged item is.
2. Write an ADR file if the decision has `needs_review: true`, or if it is not `owner_confirmed`
   and has a `confidence` other than `high`. `needs_review` wins over `owner_confirmed`.
3. Every merged decision, with or without a file, is one row in the `## Decisions` table of the PR
   body (ticket, title, decision, why). An owner-confirmed row says `owner-confirmed`.

## What a good ADR says

- `title`: the decision, not the topic.
- `options`: each option you weighed, including the one you rejected and why.
- `why`: the reason this option won, with the evidence.
- `how_to_reverse`: the exact steps to undo it.
- `confidence`: `high`, `medium` or `low`. Use `low` when you guessed.

## How an agent returns it

Return `decisions[]` in your result. Each item has `ticket`, `stage`, `title`, `context`, `options`,
`decision`, `why`, `consequences`, `how_to_reverse`, `confidence`, `needs_review`, and optionally `owner_confirmed`.
Never write an ADR file. Parallel worktrees collide on numbers. Only the ADR stage writes files.

## Design ADRs

A depth L design from `brainstorming` is an ADR with `stage: design`. It goes through `decisions[]`
and the ADR stage like any other decision. It is not written under `specs/`.

## The ADR stage

1. Collect all `decisions[]` of the run. Add `decided_by` to each. Save as
   `{"run": "<slug>", "decisions": [...]}` in a temporary file.
2. Run `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_adrs.py --input <file>`. Add `--dry-run` to preview. Exit 2 means
   bad input: fix it and run again. The script assigns the numbers. Add `--table-out <file>` to write the
   decisions table. It may write no file and print `[]`.
3. Save the printed JSON. Commit the new files in `docs/adr/` to the PR branch.
4. Build the artifact (below). Then run
   `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/write_adrs.py --render-section <written.json> [--artifact <url>]` and put the
   output, then the table file, in the PR body as `## Decisions`.

## The artifact

If the user-level `ink-artifact` skill and the Artifact tool exist, build ONE artifact per run with
`ink-artifact`: one section per ticket, `needs_review` decisions first. Keep it private. The ADR
files are the source of truth, because a private artifact may not open for reviewers.
If the Artifact tool is unavailable, skip it and link `docs/adr/` in the PR body.

## Auto mode

The ADR stage itself never asks. It writes the files, commits them and renders the section and table.
