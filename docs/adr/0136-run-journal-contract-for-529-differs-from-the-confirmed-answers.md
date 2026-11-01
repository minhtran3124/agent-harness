---
ticket: 529
stage: implement
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (ship workflow: implement)
date: 2026-11-01
---

# 0136. Run journal contract for #529 differs from the confirmed answers

## Context

The owner confirmed three answers on #529: the script itself, not an agent, writes the journal; the file is `.ship/journal-<run-id>.jsonl`; `.ship/` goes into `.gitignore`. The ticket's Verify row runs `git check-ignore .ship/journal-x.jsonl`.

The real Workflow runtime was measured during the build. It has no `fs`, `process`, `require` or `performance`; `Date.now` throws; and `import()` is a syntax error that stops the script from launching. So the script cannot write any file, and it has no clock.

## Options

- Keep the confirmed contract. Not possible: the script cannot write a file, and `import()` would stop the launch.
- An agent writes the file, at the confirmed path inside the repo. The write works, but the file lands in the owner's checkout and needs a `.gitignore` entry in every target repo.
- An agent writes the file outside the repo, next to the worktrees. No `.gitignore` entry is needed. The owner's `git status` stays clean.
- Do not write a file; return the rows only as `out.journal`. The rows are lost when the run is cancelled or killed.

## Decision

The script keeps the rows in memory and returns them as `out.journal`. One cheap agent writes them to `<parent of repoDir>/.ship-<repo>/journals/journal-<runId>.jsonl` at the end of the run and also when the run throws. If no agent can write, each row goes to the run log. There is no `.gitignore` entry.

`duration_ms` is `null` in the real runtime. `output_tokens` (the change in `budget.spent()`) is the only cost measure; it is shared by the whole turn, so compare rows and do not add them.

## Why

The confirmed answers assumed a script that can write files. The runtime cannot. An agent write keeps the file, and putting it outside the repo removes the need for a `.gitignore` entry. The rows still reach the caller if the write fails.

## Consequences

- The Verify row's `git check-ignore .ship/...` no longer applies. The check that replaces it is the test harness (`tests/workflows/harness.js`, the `journal:` cases).
- "Which stage is slowest" cannot be answered from `duration_ms` in a real run. `output_tokens` is only a rough proxy.
- An agent copies the rows, so an altered value is not detected. Only a count of parseable lines is checked.
- A run killed or cancelled without throwing leaves no file.
- Intent review, fix agents, the advisor, GIF and attach have no row.

## How to reverse

Move the journal write into the script if the runtime ever exposes a file API, and restore `.ship/` plus the `.gitignore` entry. Ask the owner to confirm or change this contract on #529.
