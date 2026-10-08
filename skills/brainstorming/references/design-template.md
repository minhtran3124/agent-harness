# Design Template

Use this template as the output contract for every `specs/<slug>/design.md`. The sections up to
Non-goals are the usual free-form design sections: keep, merge or drop them in proportion to the
change. Three after Non-goals are required — What must be true, What we do not claim and
Decisions — each with content or a `- none — <reason>` line. Decision changes appears only once a
`DC<n>` exists.

---

## Goal

_What the change achieves, in one or two sentences._

## Current state

_What exists today that the change builds on or replaces, with file pointers._

## Approaches considered

_The 2–3 approaches from brainstorming step 3, their trade-offs, and the chosen one._

## Architecture

_Components, data flow, and interfaces of the chosen approach._

## Error behavior

_What fails, how it is reported, and what the caller does about it._

## Tests

_What proves the change works, and at which evidence tier._

## Success criteria

_Observable outcomes, each with the check that proves it._

## Non-goals

_What this design deliberately leaves out of scope._

---

## What must be true

_The assumptions the design depends on. Write `- none — <reason>` when it depends on none beyond
its own text._

| ID | Assumption | Evidence now | Proven by | If false |
|---|---|---|---|---|
| A1 | _a statement the design depends on_ | _<tier>: <source label>, <date>, <location>_ | _intended SC / task / check_ | _what breaks, and the fallback_ |

- **IDs** are `A1, A2, …`. Before approval, renumber them to stay sequential when a row is
  deleted. After approval an ID is never reused or renumbered, and a row is never deleted: a
  `DC<n>` that drops an assumption sets its *Proven by* to `retired by DC<n>`.
- **Evidence now** has two parts. The **tier** says how strong the evidence is: `traceability`
  (the structure matches: an ID exists, a reference resolves), `provenance` (re-derived from the
  source of truth: a file read, a value rebuilt), `truth` (the behavior was re-run and its result
  compared), or `none yet` when no check has confirmed the assumption. A bare `none yet` is valid;
  it may also carry an `Inference` source that says what the belief rests on. The **source** uses
  the research-brief Evidence Ledger labels `Local`, `Upstream`, `Docs` or `Inference`, followed by the date it was read and its
  location. Example: `provenance: Local, 2026-10-08, review-loop.md`.
- **Proven by** is never empty. It is the intended `SC-n`, task or check, `accepted risk: <reason>`,
  or `retired by DC<n>`. Unless retired, `writing-plans` binds it to a concrete `SC-n` or task.
- **If false** is never empty: say what breaks and the fallback.
- A number inside an assumption still carries its number label (see "Number labels" below).

## What we do not claim

_Guarantees a reader may expect that the shipped work will not give. Unlike Non-goals, which bound
the scope, this names expected guarantees that are absent. Write `- none — <reason>` when there
are none._

| Guarantee a reader may expect | Why not |
|---|---|
| | |

## Decisions

> To reopen a settled decision after approval: Rule 4 STOP and ask the user, then add a `DC<n>`
> entry under `## Decision changes`, add the new decision as the next `D<n>` row (`settled`), set
> the old row to `superseded by DC<n>`, and add a pointer line in `SUMMARY.md` `### Deviations`.

| ID | Decision | Consequence | Status |
|---|---|---|---|
| D1 | _what was decided_ | _what follows from it_ | settled |

_Copy the pointer line above into every design that has a decisions table. Write
`- none — <reason>` (without the table) when the design settles no decision._

- **Status** is exactly `settled` or `superseded by DC<n>`. An unsettled choice is not a decision
  yet; it stays in the design's prose until it is settled. Readers and reviewers treat only
  `settled` rows as current.
- **When a decision becomes `settled`.** A `D<n>` row is `settled` from the moment the user
  approves the design (brainstorming step 5 plus the spec review loop). Before approval, rows are
  drafts: edit, delete and renumber them directly, with no `DC<n>`.
- **Reopening.** A `settled` decision is reopened only by a dated `DC<n>` entry that cites
  evidence showing the decision is wrong. The old row stays in the table with its status set to
  `superseded by DC<n>`. The new decision is a new `D<n>` row with the next free ID and status
  `settled`, and the `DC<n>` entry names it (`new decision: D<n>`).
- **Revision pass.** A later brainstorming run on a spec whose design was already approved is a
  revision pass. Its settled rows are not drafts: each change to one is a `DC<n>`, and the design
  reviewer applies the decision-change checks. A `DC<n>` written during planning or implementation
  is reviewed at the next revision pass, if one happens. The reviewer sees only the current design,
  not the approved one, so it checks that `DC<n>` entries are consistent; it cannot detect a
  settled row edited in place without one.
- **After approval** (during planning or implementation), reversing a settled decision changes the
  approved design, so it is a Rule 4 STOP under `rules/auto-correct-scope.md`: ask the user before
  writing the `DC<n>`. The design reviewer loop is not re-run. The record is the `DC<n>` entry plus
  one line in `SUMMARY.md` `### Deviations` that points to it. `### Deviations` normally holds
  Rule 1–3 auto-fixes (`rules/auto-correct-scope.md` "Reporting"); this pointer line is a
  deliberate extension of that reporting, not a misfiled entry.
- If the `DC<n>` adds or changes an `A<n>` after `PLAN.md` exists, the same Rule 4 step updates
  the plan's `### Assumption coverage`. The plan reviewer is not re-run for it.

## Decision changes

_Records changes made after approval only. Omit this section while it has no entries. IDs are
`DC1, DC2, …`, sequential and never reused._

- DC1 — _YYYY-MM-DD_ — reopens D<n> — evidence: _measurement or source_ — new decision: D<n>

---

## Number labels

_A rule for every section above, not a section to copy into the design._

A number is **load-bearing** when a decision, target, threshold or Success Criterion depends on it.
Each value of a load-bearing number carries exactly one label:

- `prediction` — an estimate not yet measured;
- `budget` — a limit we chose;
- `measured <YYYY-MM-DD> <source>` — a value observed, with its date and where it came from.

When a measurement replaces a prediction, keep the prediction with its label and append the
measurement beside it with its own: `80 ms (prediction) → 92 ms (measured 2026-11-02 <run>)`.
Illustrative numbers stay unlabelled.
