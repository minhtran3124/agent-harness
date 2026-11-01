---
ticket: 529
stage: implement
status: accepted
needs_review: false
confidence: high
decided_by: claude (ship workflow: implement)
date: 2026-11-01
---

# 0136. Run journal contract for #529 differs from the confirmed answers

## Context

The owner confirmed three answers on #529: the script itself, not an agent, writes the journal; the file is `.ship/journal-<run-id>.jsonl`; `.ship/` goes into `.gitignore`. The ticket's Verify row runs `git check-ignore .ship/journal-x.jsonl`. The ticket's purpose is to answer "which stage is slowest" and "which stage retries most" from one file.

The real Workflow runtime was measured during the build. The script runs in a sandbox that has no `fs`, `process`, `require` or `performance`; `Date.now` throws; and `import()` is a syntax error that stops the script from launching. So the script (`ship.js`) can neither write a file nor read a clock.

The runtime itself keeps, for every run, a `journal.jsonl` (one `started` and one `result` line per agent, with `label` and `phase`) and one `agent-<id>.jsonl` transcript per agent with a timestamp and token usage on every message. This was checked on a real 48-agent run: all 48 agents join to a label, and the slowest stages come out right.

## Options

- Keep the confirmed contract. Not possible: the script cannot write a file or read a clock.
- Have a cheap agent write the file from rows the script holds. Rejected: an agent has to retype every row, an altered value is not detected, it costs a call per run, and `duration_ms` would still be `null`.
- Have the main session write `out.journal` to a file after the run. Works, but it still has no times or tokens.
- Keep only what the script knows (`ticket`, `stage`, `model`, `status`, `retries`) in `out.journal`, and take time and tokens from the runtime's transcripts with a separate script.

## Decision

`ship.js` returns the rows as `out.journal` and logs each one as `journal row: {...}` at the end of the run and when the run throws. It writes no file, spends no agent on the journal, and takes no `runId`.

`plugins/harness/scripts/run_report.py` reads a run's `journal.jsonl` and `agent-*.jsonl`, groups the agents by the stage in their label, and prints agent time, wall time and output tokens per stage, slowest first. With `--journal FILE` (out.journal as JSON, or the run log) it adds each row's `status` and `retries`.

## Why

The confirmed answers assumed a script that can write files and read a clock. The runtime offers neither, but it records both facts itself and exactly: per-agent tokens are not mixed between parallel stages, as `budget.spent()` would be. The script keeps only the parts the runtime cannot know, such as the status judged by the pipeline.

## Consequences

- The Verify row's `git check-ignore .ship/...` no longer applies. The checks that replace it are the `journal:` cases in `tests/workflows/harness.js` and `scripts/test_run_report.py`.
- The report depends on the runtime's run directory layout, which belongs to Claude Code and can change. The script reports a missing file and does not guess.
- Stages are matched by the agent label. A renamed label in `ship.js` changes the stage name in the report.
- Intent review, fix agents, the advisor, GIF and attach have no script row, but they appear in the report as stages of their own, because every agent has a transcript.
- A run whose transcripts were deleted cannot be reported.

## How to reverse

Restore a file write in the script if the runtime ever exposes a file API and a clock, and restore `.ship/` plus the `.gitignore` entry. The owner confirmed this contract on 2026-11-01 (ticket #529); change it only with the owner.
