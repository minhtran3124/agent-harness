# Specs

Design docs, research briefs, and implementation plans. Each feature/change gets its own spec directory.

## Slug Convention

`specs/<slug>/` where `<slug>` is short kebab-case. Some projects prefix with date: `specs/YYYY-MM-DD/<slug>/`.

Pick one convention per repo and stick with it. This project uses: **`<slug>/`** (flat) — update this line if you change it.

## Files Per Spec

| File | Produced by | Purpose |
|---|---|---|
| `design.md` | `/brainstorming` | Approved design — the WHAT and WHY |
| `research-brief.md` | `/xia2` | What already exists, alternatives, lightest path |
| `plan.md` | `/writing-plans` | Task-by-task plan (XML tasks per `rules/plan-format.md`) |

## Lifecycle

```
/brainstorming → design.md
/xia2          → research-brief.md
/writing-plans → plan.md
/using-git-worktrees → worktree + branch
/subagent-driven-development | /executing-plans → implementation
/compound → crystallize learnings into docs/solutions/
/finishing-a-development-branch → PR (never merges)
```

See [../skills/README.md](../skills/README.md) for the full workflow map.

## State File

`STATE.md` at this level tracks the currently-active spec and last action. It is updated by skills as work progresses and by the `state-breadcrumb.sh` hook at session end.
