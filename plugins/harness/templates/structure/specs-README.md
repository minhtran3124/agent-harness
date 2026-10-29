# Specs

`specs/` is local scratch space. Keep it gitignored: nothing here is committed or shared.

Every ticket gets one folder, `specs/<slug>/`, at every depth (S, M and L). Intake picks the slug:
the issue number and a short title (`412-profile-page`), or a short kebab name for free text. Every
later step uses the same slug.

## Flow files

| File | Written by | What it holds |
|---|---|---|
| `intent.md` | `intake`; `grilling` adds to it | The request verbatim, the goal, the acceptance criteria, out of scope, the verdict and depth, and the confirmed decisions. |
| `design.md` | `brainstorming` (depth L); `writing-plans` (depth S and M) | The chosen approach and the options it beat. At depth S and M this is a few lines. |
| `decision.md` | every step that decides | One entry per decision: title, decision, why, how to reverse, and the ADR path when one was written. |
| `plan.md` | `writing-plans` | The steps, each with Files, Effort, Done-when and a parallel group. At depth S this is one or two steps. |
| `summary.md` | `finishing-a-development-branch` | What shipped: branch, PR, commits, the verify commands and their output, review results, and any deviation from the plan. |

The templates are in the harness plugin, `templates/specs/`. Every file starts with the same
`Ticket · Depth · Date` line and keeps every heading at every depth; an empty section says `none`.
IDs link the files instead of copies: `AC<n>` in `intent.md`, cited by plan steps (`Covers:`) and
the summary's Verify table; `D<n>` in `decision.md`, cited by the summary.

Extra files when they apply: `research-brief.md` (`xia2`, depth L) and `diagnosis.md`
(`diagnosing-bugs`).

A step that runs inside a workflow (`Mode: auto`) writes no `specs/` file. It returns the text, and
the workflow script writes the files to the main checkout's `specs/<slug>/`, so they stay after the
worktree is removed.

## What stays tracked

`specs/` is a working record, not the source of truth. Anything worth keeping goes to a tracked
place as well:

- durable decisions and depth L designs: `docs/adr/` (`decision.md` links them)
- reusable learnings: `docs/solutions/`

Delete a folder when you no longer need it.

See [../skills/README.md](../skills/README.md) for the workflow map.
