# trust-metrics-stage-indicators — Summary

Lane: tiny
Confidence: high
Reason: one docs file, definitions only; no manifest hard gate (docs/harness-experimental/ is not hooks, settings, templates, or workflow-engine prose)
Flags: none
Affects: docs/harness-experimental/trust-metrics.md
Input-type: harness improvement
Route: tiny — branch docs/trust-metrics-stage-indicators, direct patch, quick-check proof
Escalate: no

> `Lane` drives **ceremony** (how much proof). `Confidence` drives **interruption**
> (whether a human is asked). A hard gate forces `high-risk`. Low confidence or an
> ambiguous direction escalates regardless of lane — see `rules/orchestration.md`.

### Intent

Intent-source: specs/trust-metrics-stage-indicators/intent.md @ 5fda6a666eae2027778d6391ee9a9a42d57f722d

"let merge this PR and start the next itme" — the next item in the suggested order of
`docs/research/2026-10-10-ai-native-sdlc-playbook-adoption.md` §6 is E6:

| **E6** | **Define one leading + one lagging indicator per workflow stage** in `trust-metrics.md` (definitions only, no tooling yet) — e.g. intake→PLAN latency, task-review first-pass rate, plan drift, review-escape rate | All plays' "How to measure it" | `docs/harness-experimental/trust-metrics.md` | tiny |

§8 adds: E6 could now include "intent edits after pin" (count of re-pins per slug), the playbook's
lagging indicator for this play.

### Intake notes

- auto-approved: tiny/high
- "Next item" resolved from §6 "Suggested order" (`E6 → E2 → E1 → …`); E4 shipped in PR #284.
- Branch cut from `sdlc` before the intent commit although the draft procedure only cuts on
  main/master: `sdlc` is this repo's shared integration branch (advisory A3 of
  intent-draft-from-chat).
- Placement constraint: `scripts/bookkeeping.sh` appends ledger rows to the end of the file, so
  the new section goes above `## Ledger`.

## What changed

Added `## Stage indicators` to `docs/harness-experimental/trust-metrics.md`, above `## Ledger`: one leading and one lagging indicator for each of five workflow stages (Intake, Plan, Implement, Review chain, Ship), each with a definition and unit, the better direction, and a tracked data source. It includes the four §6 examples and §8's "intent edits after pin". A closing paragraph names the known data gaps. Definitions only; no script or hook changed.

### Rationale

Sources are limited to tracked files (Git, SUMMARY, PLAN, `events.jsonl`) so M4 can compute every indicator without `.harness-state/`. Design, research, and plan are one stage because only PLAN.md has a commit timestamp and a file list that every planned run produces.

### Alternatives considered

- Separate Design and Research stages: rejected; neither leaves a tracked, comparable signal on most runs (design.md exists only on a fork or high-risk).
- Under-classification rate as the Intake lagging indicator: it is already the ledger's stated purpose; §8 asked for intent edits after pin, so that took the one lagging slot.

### Deviations

- none

### Verify

| Check | Command | Exit | Notes | Criterion |
| --- | --- | --- | --- | --- |
| five leading and five lagging rows | `python3 -c "import sys;t=open('docs/harness-experimental/trust-metrics.md').read();p=chr(124);sys.exit(not(t.count(p+' leading '+p)==5 and t.count(p+' lagging '+p)==5))"` | 0 | 5 leading, 5 lagging | |
| Ledger is the last section (bookkeeping.sh appends) | `python3 -c "import re,sys;h=re.findall(r'^## .*',open('docs/harness-experimental/trust-metrics.md').read(),re.M);sys.exit(h[-1]!='## Ledger')"` | 0 | headings: Stage indicators, Ledger | |
| status script still reads ledger rows | `bash scripts/harness-status.sh` | 0 | last 5 rows are ledger rows (2026-09-29..2026-10-02) | |
| full suite | `bash scripts/run-tests.sh` | 0 | 880 passed, ALL GREEN | |

### Not auto-verified

- That each indicator is computable from its named source — reached traceability (sources exist: `events.jsonl` `ts`/`to_state`, SUMMARY sections, PLAN `Files`); not re-run because no script computes them yet (M4).

### Rollback

- `git revert a044b3e 5fda6a6`

### Harness-Delta

- backlog — `scripts/harness-status.sh` prints ledger columns shifted by one since the `Affects` column was added (`lane=` shows Affects, `conf=` shows Flags). Pre-existing; not changed here.
- backlog — the draft-intent procedure cuts a branch only on main/master; on `sdlc` (shared integration branch) intake would commit there (intent-draft-from-chat advisory A3).
