# Specs

Design docs, research briefs, and implementation plans. Each feature/change gets its own spec directory.

## Slug Convention

`specs/<name>/` where `<name>` is the spec folder name, derived at intake from the ticket source:

| Ticket source | Folder name | Example |
|---|---|---|
| GitHub issue | `gh-<issue#>-<slug>` | `specs/gh-121-spec-folder-prefix/` |
| Linear ticket | `lin-<TICKET-ID>-<slug>` | `specs/lin-ENG-315-user-quota/` |
| No ticket | `<slug>` (plain) | `specs/fix-hook-matching/` |

`<slug>` is short kebab-case in all three forms. The prefix and slug are lowercase; only the
Linear ticket ID keeps its native (upper) case — do not normalize it. Folders created before
this convention are grandfathered — never rename them; every gate treats the full folder name
as an opaque slug (`specs/<anything>/`). Branch names inherit the prefix for free via
`<type>/<slug>` (e.g. `feat/gh-121-spec-folder-prefix`).

Some projects prefix with date instead: `specs/YYYY-MM-DD/<slug>/`. Pick one convention per
repo and stick with it. This project uses: **ticket-source prefix** (table above) — update
this line if you change it.

## Files Per Spec

| File | Produced by | Purpose |
|---|---|---|
| `SUMMARY.md` | `feature-intake` | **Always written, every lane** — Lane/Confidence/Reason, the
  user's request verbatim under `### Intent`, plus `### Verify` / `### Rollback` / `### Deviations`.
  `commit-quality-gate.sh` gates commits on it and `intent-review` reads `### Intent` as its oracle. |
| `ESCALATIONS.md` | any skill that escalates | Only when a hard gate or ambiguity stops the work.
  Deny-on-no-response: a commit touching the slug is blocked while a `decision: pending` block stands. |
| `design.md` | `brainstorming` | Approved design — the WHAT and WHY |
| `research-brief.md` | `xia2` | What already exists, alternatives, lightest path |
| `PLAN.md` | `writing-plans` | Task-by-task plan (markdown `### Task` sections per `rules/plan-format.md`; the uppercase name is what the hooks and renderer match) |

## Lifecycle

```
feature-intake → SUMMARY.md (lane + confidence + verbatim intent)
brainstorming  → design.md
xia2           → research-brief.md
writing-plans  → PLAN.md
using-git-worktrees → worktree + branch
subagent-driven-development → implementation
compound → crystallize learnings into docs/solutions/
finishing-a-development-branch → PR (never merges)
```

See [../skills/README.md](../skills/README.md) for the full workflow map.

## State File

`STATE.md` at this level tracks the currently-active spec and last action. It is updated by skills as work progresses and by the `state-breadcrumb.sh` hook at session end.
