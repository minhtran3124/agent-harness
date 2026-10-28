---
name: decision-record
description: Record every decision a model makes on its own during an autonomous run as a reviewable ADR. Stage agents return `decisions[]`; the final ADR stage writes `docs/adr/NNNN-*.md` by script. Use when a stage decides without asking a human.
allowed-tools: Read, Write, Bash, Skill
---

# Decision Record

## When to record

Record a decision when you choose between options without asking a human. Ask the table first.

| Situation | Action |
|---|---|
| Reversible and inside the ticket | Decide. Record it. `needs_review: false`. |
| Affects another ticket or a public contract | Choose the safer option. Record it. `needs_review: true`. |
| Contradicts a confirmed answer, or is dangerous | Do not do that part. Record why. `needs_review: true`. |

## What a good ADR says

- `title`: the decision, not the topic.
- `options`: each option you weighed, including the one you rejected and why.
- `why`: the reason this option won, with the evidence.
- `how_to_reverse`: the exact steps to undo it.
- `confidence`: `high`, `medium` or `low`. Use `low` when you guessed.

## How an agent returns it

Return `decisions[]` in your result. Each item has `ticket`, `stage`, `title`, `context`, `options`,
`decision`, `why`, `consequences`, `how_to_reverse`, `confidence`, `needs_review`.
Never write an ADR file. Parallel worktrees collide on numbers. Only the ADR stage writes files.

## The ADR stage

1. Collect all `decisions[]` of the run. Add `decided_by` to each. Save as
   `{"run": "<slug>", "decisions": [...]}` in a temporary file.
2. Run `python3 scripts/write_adrs.py --input <file>`. Add `--dry-run` to preview. Exit 2 means
   bad input: fix it and run again. The script assigns the numbers.
3. Save the printed JSON. Commit the new files in `docs/adr/` to the PR branch.
4. Build the artifact (below). Then run
   `python3 scripts/write_adrs.py --render-section <written.json> [--artifact <url>]` and put the
   output in the PR body as `## Decisions`.

## The artifact

If the user-level `ink-artifact` skill and the Artifact tool exist, build ONE artifact per run with
`ink-artifact`: one section per ticket, `needs_review` decisions first. Keep it private. The ADR
files are the source of truth, because a private artifact may not open for reviewers.
If the Artifact tool is unavailable, skip it and link `docs/adr/` in the PR body.

## Auto mode

The ADR stage itself never asks. It writes the files, commits them and renders the section.
