---
ticket: 618
stage: design
status: accepted
confidence: high
decided_by: owner
date: 2026-11-11
---

# 0032. Check tickets with no app with a plan-blind qa-verifier

## Context

The UAT phase of `ship.js` skipped every ticket whose `Verify:` kind is `docs`. That kind covers docs, config, CLI, scripts and plugin files, so most tickets of this repo got no independent check after the build. They had only the `qa-writer` tests (written before the code) and the `Verify:` row, which the implementer can see.

## Options

- Leave `docs` tickets unchecked (the old flow).
- Run the `uat` skill on them. It needs a running app and a config, so it would report blocked every time.
- Add a second agent in the same stage: a plan-blind `qa-verifier` that runs commands and reads delivered files.

## Decision

Add the `qa-verifier` agent (Sonnet 5.5, `medium`, tools Bash, Read, Glob, Grep) and call it from `stageUat` for a `docs` ticket at depth M and L. Depth S is skipped with the log line `skipped: docs ticket at depth S`. It gets the same stripped issue body and owner block as the UAT agent, in its own worktree, with no config path. It reuses the UAT fix round, rerun, decisions and PR sign-off, under the names `QA check` and `QA check not run for #<n>`. The agent returns one row per AC (`PASS`, `FAIL` or `not-checkable`) and `head_sha`. Its blindness is a prompt rule; no hook enforces it.

## Why

A second agent in the same stage reuses all the UAT machinery and keeps the check independent of the plan and the diff. Running the `uat` skill on a ticket with no app cannot work. Leaving the tickets unchecked keeps the gap.

## Consequences

Enables: an independent check for most tickets of this repo. Costs: one more Sonnet 5.5 call per `docs` ticket at depth M and L, plus one fix call and one rerun on a failed AC. A `docs` ticket can now end blocked with reason `UAT AC failed`, or get a `needs_review` decision when the check cannot run. A `not-checkable` row is never a pass, so a ticket whose ACs no command can show passes with nothing checked; the PR sign-off lists those rows. Local mode still skips the phase. The agent cannot prove it stayed blind.

## How to reverse

Restore the `kind === 'docs'` skip in `stageUat`, remove the `qa` branch of `uatAgent`, and delete `plugins/harness/agents/qa-verifier.md` and its tests.
