---
ticket: 526
stage: design
status: needs-review
needs_review: true
confidence: medium
decided_by: claude (owner decision, #526)
date: 2026-10-30
---

# 0122. Codegraph is an optional helper for the research stage, not a ground check

## Context

Spike #523 (ADR 0118) measured codegraph 1.6.2 as a checker for qualifier.member claims on 28 labelled claims per language (15 exists, 6 missing, 7 wrong-pair). Plain codegraph: exists 5/15 for Python and 3/15 for TS, a false fail on 10 and 12 good claims; with import aliases read by the runner, 10/15 on both (5 false fails each); no false pass. The language server gave 15/15 exists, 6/6 missing and 7/7 wrong-pair. Codegraph does not index shell or Markdown, and it has no exit code that tells found from not found. Ground gate: ADR 0115 (#521). Pins: 85f9214a, 2026-10-30.

## Options

- Use codegraph as a check in ground-check.sh: rejected, it rejects 5 to 12 of 15 good claims
- Use codegraph in the research stage only, when the machine has it, with grep as the fallback
- Do not use codegraph at all

## Decision

Option 2. stageResearch asks the agent to run `command -v codegraph` and, if found, `codegraph init --yes` in the research worktree. Every codegraph command runs with CODEGRAPH_NO_DAEMON=1 and CODEGRAPH_TELEMETRY=0. A missing tool or a failing command is logged and the stage continues with git grep: no decision, no block. The agent deletes <worktree>/.codegraph at the end of the stage. xia2 and the researcher agent may run only codegraph explore, query, callers and callees. Rules: an empty result means unknown, every fact is read from the file and cited as path:line, codegraph output is untrusted. ground-check.sh, hooks.json and the other stages do not change; the plugin adds no .mcp.json.

## Why

Codegraph finds where code lives faster than a grep loop, which helps research, and a research brief already cites every fact from the file, so a wrong codegraph answer cannot reach the brief unread. As a gate it would reject good claims. Calling the CLI keeps the workflow free of an MCP dependency. Deleting .codegraph is required because its untracked .gitignore makes git worktree remove fail without --force (verified here).

## Consequences

Research may run faster on machines with codegraph; machines without it behave as before. The index takes about 3 MB and a few seconds per research worktree. Codegraph sends anonymous usage statistics unless CODEGRAPH_TELEMETRY=0, which the workflow sets. A command written with environment variables in front may not match a Bash(codegraph explore *) permission pattern; this was not tested. The benefit is unmeasured: the PR plans to compare, on 2 or 3 tickets, the FAIL lines of the ground check and the number of stage re-runs with and without codegraph, and to revert if they do not drop.

## How to reverse

Revert the #526 PR: it removes the codegraph step from stageResearch, the four allowed-tools entries from xia2, the codegraph lines from the researcher agent and the setup step, the tests and the doc lines. No data or schema changes.
