---
problem_type: decision
module: decision-record/adr
tags: adr, decision-record, needs-review, boundary, lifecycle, review-note
severity: standard
applicable_when: When you change how the harness decides which decisions get an ADR file, how an ADR is numbered or closed, or where a scope note is recorded.
supersedes: null
confidence: high
confirmed_at: 2026-11-05
affects:
  - docs/adr/README.md
  - plugins/harness/skills/decision-record/SKILL.md
  - plugins/harness/scripts/write_adrs.py
  - docs/hooks.md
---
## Goal

Answer the five questions of #560 about how the harness creates ADRs. This note reviews the repo at
commit `1ab05bc`, so its counts stay true after later changes (for example #566). Each change it
proposes is a separate follow-up issue in the milestone.

## Evidence at 1ab05bc

- `git ls-tree --name-only 1ab05bc docs/adr/` lists 40 files: 38 ADRs plus `README.md` and `TEMPLATE.md`.
- Front-matter `status:` of the 38 ADRs: 25 `needs-review`, 13 `accepted`
  (`git grep -h -E '^status:' 1ab05bc -- docs/adr`).
- #560 says 26 open. `git grep -l needs-review 1ab05bc -- docs/adr` returns 26 files, but one is
  `README.md`, which only mentions the word. The count of real open ADRs is 25 of 38.
- 8 ADR file names contain `boundary` (0112, 0123 to 0127, 0133, 0135). 6 are `UAT not run for #n`
  (0100 to 0103, 0107, 0132).

## 1. Purpose: who reads an ADR, and when

An ADR records a significant decision that an agent made without blocking the run. The reader is the
PR reviewer, once, in the PR. `docs/adr/README.md` says it lets a reviewer see "what was decided,
why, and how to undo it, without reading the whole diff". A future agent is a second reader only by
accident: the single skill that searches the folder is `xia2` (`plugins/harness/skills/xia2/SKILL.md:14`).
The other skills name one file, `0001-workflow-capabilities.md`, by path.

## 2. Criteria: is `needs_review` the right gate

No as the only gate. `needs_review` is a flag the stage agent sets itself. `write_adrs.py` writes a
file for every flagged decision (`docs/adr/README.md`, "Which decisions get a file"), and a flag
costs the agent nothing. The result is files for small choices: the 6 `UAT not run` records and the
`boundary` records are all flagged.

Keep a decision for a file only when all of these hold:

- **Impact:** it changes harness behavior, a data or config contract, or how users work.
- **Real trade-off:** at least two options that each cost something, and the choice is hard to reverse.
- **Not on the exclusion list:** scope notes, "X not run" outcomes, and a choice the ticket text
  already settled.

This is close to the three-condition gate of #311 (hard to reverse, surprising without context, real
trade-off). The impact condition and the exclusion list make it checkable by script and by a
reviewer. Every decision still gets a row in the `## Decisions` PR table.

## 3. Side effects

- **Noise:** 25 of 38 ADRs are still `needs-review`. Nothing sets them to `accepted`, so the status
  carries no signal (see answer 5).
- **Duplicates (#459):** pairs that restate one decision: 0105 and 0106 (bare number after `#n`),
  0109 and 0113 (merge-guard fails closed), 0129 and 0130 (ask for the plain merge form).
- **Number churn:** the 2026-10-29 prune renumbered the folder to 0001-0010
  (`docs/adr/README.md`, "Pruned records"). `docs/hooks.md:70` still says "see ADR 0007" for hooks in
  Workflow agents, but 0007 is now "Infrastructure failure of UAT does not fail the ticket". The old
  number points at the wrong file.
- **Two stores (#458):** decisions also live as `problem_type: decision` entries in
  `docs/solutions/` (for example `harness/gap-closure-decisions.md`). `brainstorming` reads that
  track, `xia2` reads both, and nothing links the two.
- **Token cost:** only `xia2` searches `docs/adr/`, and only when it runs. The folder is 38 files and
  grows with every run that flags a decision; most of the growth is the noise above.

## 4. Boundary records

A `Boundary:` record is a scope note, not a decision. Record it as a row in the `## Decisions` PR
table and as a `Needs your decision` line in the PR body. Write no file. The reviewer sees it at the
moment it matters, and it does not outlive the PR.

## 5. Lifecycle

Nobody closes an ADR today: `write_adrs.py` writes `status: needs-review` and no step changes it.
Write the ADR as `accepted`. The PR reviewer already reads and approves the ADR in the PR, so merging
the PR is the acceptance. Remove the `needs-review` status value. Use `superseded` only when a later
ADR replaces one, set by the author of the later ADR.

## Changes proposed (one follow-up issue each)

1. Gate: apply the impact, trade-off and exclusion rules in `write_adrs.py` and the `decision-record` skill.
2. Prune: delete the 26 ADRs that fail the gate and renumber the 12 that stay to 0001-0012; fix
   `docs/hooks.md:70`.
3. Lifecycle: write new ADRs as `accepted`; drop `needs-review`.
4. Boundary: stop writing files for `Boundary:` decisions; add the `Needs your decision` line.
5. Stores (#458): keep both stores and document which record goes where.
