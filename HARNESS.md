# HARNESS.md — How this repo's workflow works

This repo is a **skills framework with a thin judgment harness on top**. This file explains, in plain terms, what "the harness" is and how it shapes the way work flows.

For the full skill inventory and handoff map see [`skills/README.md`](skills/README.md).

---

## 1. Two layers: the engine and the harness

| Layer | What it is | Lives in |
|---|---|---|
| **The engine** (skills) | Invocable `/skills` that *do* the work: intake, design, research, plan, build, review, ship. Each has hard gates and a defined handoff. | `skills/`, `agents/` |
| **The harness** | A small control layer: one behavioral rule, a few hooks, and permission denies. | `rules/behavior.md`, `hooks/`, `settings.json` |

Claude Code is the only supported runtime.

## 2. The one principle everything turns on

> **Ceremony scales with the size of the change. Human interruption scales with ambiguity.**

A small clear change runs straight through. An important or unclear one stops and asks the owner.

## 3. How a change flows

```
ticket → /intake → verdict + depth → build → review → ship
```

1. **`/intake` runs first.** It returns a verdict (READY, CONFIRM, GRILL or BLOCKED) and a depth (S, M or L).
2. **The depth picks the path:**

   | Depth | Path |
   |---|---|
   | **S** | `implement` with the plan in the prompt |
   | **M** | `writing-plans`, then `implement` |
   | **L** | `brainstorming`, `xia2`, `writing-plans`, then `implement` |

   A bug fix first runs `diagnosing-bugs` (root cause proved in six gated phases before any fix).
3. **Review and ship.** `/code-review` and `intent-review` check the diff. `finishing-a-development-branch` pushes and opens the PR. A human merges.

## 4. What is enforced and what is judgment

- **Enforced by code:** `hooks/secrets-scan.sh` blocks a commit with a staged secret or `.env`. `settings.json` `permissions.deny` blocks `.env` reads, force-push and push to `main`/`master`. See `docs/hooks.md`.
- **Judgment, set by `rules/behavior.md`:** cite your search surface before claiming absence, name an ambiguity instead of resolving it silently, confirm an interface before you use it, deliver the whole asked scope, and write plainly.
- **Claims need evidence.** "Done" needs a command that was actually run and its exit code. A bug needs a failing repro test first, then the fix.

## 5. Stop and ask the owner when

A change touches auth or authorization, data migration or deletion, a public contract, an external provider, `settings.json` or `hooks/`, or removes a test or a feature. Also stop when the direction is ambiguous. No hook decides this; the agent applies it as judgment.

## 6. Pointers

| Want to… | Read |
|---|---|
| See all skills + the handoff map | `skills/README.md` |
| Understand the intake verdict and depth | `skills/intake/SKILL.md` |
| Know what a hook enforces | `docs/hooks.md`, `CLAUDE.md` → Hooks table |
| See the behavioral rule | `rules/behavior.md` |
