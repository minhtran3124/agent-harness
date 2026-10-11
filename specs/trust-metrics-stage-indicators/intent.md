# Intent: Define per-stage leading and lagging indicators in trust-metrics.md

Author: Minh Tran
<!-- Set Status to approved or draft. Intake proceeds only on approved. -->
Status: approved

## Problem

The trust-metrics ledger records one row per shipped task, but it defines no indicator per
workflow stage, so there is no agreed way to tell whether a stage is getting better or worse.
Every playbook play pairs its practice with a "how to measure it" (research note §6, E6).

## Proposed outcome

`docs/harness-experimental/trust-metrics.md` defines one leading and one lagging indicator for
each workflow stage, for example intake→PLAN latency, task-review first-pass rate, plan drift,
review-escape rate, and intent edits after pin (re-pins per slug). These are definitions only.

## Affected users and systems

Harness maintainers who read the ledger (assumed). The later indicator script (M4) and control
bands (H2) will compute these definitions (assumed).

## Constraints

- Definitions only: no script, hook, or CI change.
- Each indicator names its data source, which must already exist in Git, `SUMMARY.md`, `RUN.json`/`events.jsonl`, or the ledger, because `.harness-state/` is gitignored (assumed).
- The `## Ledger` table stays the last section of the file: `scripts/bookkeeping.sh` appends rows to the end of the file (assumed).
- No new line may start with `| YYYY-MM-DD`: `scripts/harness-status.sh` reads such lines as ledger rows (assumed).

## Out of scope

- Computing the indicators (M4) or alerting on them (H2, H3).
- Changing existing ledger rows or columns (assumed).

## Open questions

none

## What success looks like

Each stage in the workflow chain (intake, design and research, plan, implement, review chain,
finish) has exactly one leading and one lagging indicator, each with a definition, unit, and data
source (assumed). The ledger table is still last, and `bash scripts/run-tests.sh` stays green
(assumed).

## Original request

"let merge this PR and start the next itme" — the next item in the suggested order of
`docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §6 is E6:

| **E6** | **Define one leading + one lagging indicator per workflow stage** in `trust-metrics.md` (definitions only, no tooling yet) — e.g. intake→PLAN latency, task-review first-pass rate, plan drift, review-escape rate | All plays' "How to measure it" | `docs/harness-experimental/trust-metrics.md` | tiny |

§8 adds: E6 could now include "intent edits after pin" (count of re-pins per slug), the playbook's
lagging indicator for this play.
