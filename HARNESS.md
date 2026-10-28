# HARNESS.md — How this repo's workflow works

This repo is a **skills framework with a risk/trust harness on top**. This file explains, in plain terms, what "the harness" is and how it shapes the way work flows.

For the full skill inventory and handoff map see [`skills/README.md`](skills/README.md).

---

## 1. Two layers: the engine and the harness

| Layer | What it is | Lives in |
|---|---|---|
| **The engine** (skills) | Invocable `/skills` that *do* the work — brainstorm, research, plan, build, review, ship. Each has hard gates and a defined handoff. | `skills/`, `agents/` |
| **The harness** (risk/trust) | A thin control layer that decides, *before* the engine runs, **how much process** a change needs and **when to involve a human**. | `skills/feature-intake/`, `hooks/`, `rules/` |

The engine answers *"how do I build this?"* The harness answers *"how careful should I be, and
who needs to approve?"*

### Runtime boundary

Claude Code is the only supported runtime.

## 2. The one principle everything turns on

> **Ceremony scales with risk. Human interruption scales with ambiguity.**

These are two independent dials:
- **Risk** decides how much *proof and process* (planning, reviews, evidence) a change carries.
- **Ambiguity / confidence** decides whether a *human* is asked — never to classify risk, only to confirm intent or authorize a dangerous boundary.

A high-risk-but-clear change runs autonomously through heavy proof. A tiny-but-unclear change stops to ask. Risk ≠ interruption.

## 3. How a change flows

```
request → /feature-intake → Lane + Confidence → route → build → hooks corroborate → ship
```

1. **`/feature-intake` runs first.** It classifies the request with a 10-flag risk checklist +
   hard gates, and states the lane and confidence in its reply.
2. **The lane picks the path:**

   | Lane | Path | Plan? | Human gate |
   |---|---|---|---|
   | **tiny** | fresh branch, then direct `Edit` | no | none (hooks are the safety net) |
   | **normal** | `/implement` | yes | only if low confidence / ambiguous |
   | **high-risk** | full chain: `/brainstorming → /xia2 → /writing-plans → build` | yes | only on ambiguity or a hard gate |

   An `Input-type: bug fix` first runs `diagnosing-bugs` (root cause proved in six gated phases
   before any fix), then its lane route.

3. **Confidence decides escalation.** Low confidence (any lane), or a hard gate, → stop and ask the owner.
4. **Hooks corroborate the claim.** At commit time the diff is checked against the declared lane — the agent can't classify a risky change as "tiny" and slip it through. Warn-mode gates (`workflow-engine`, `weakening-validation`) print a note instead of blocking.

## 4. How the harness impacts the workflow

- **Less ceremony on small work.** Typo/copy/narrow edits skip planning entirely (tiny lane).
- **More proof on risky work.** Auth, migrations, schema, public contracts, and high-blast files force `high-risk` — full plan + reviews + a recorded rollback.
- **The human is asked less, but at the right moments.** Approval is gated on *ambiguity*, not on every step. Clear work proceeds with a notice; unclear work blocks.
- **Claims must be backed by evidence.** "Done" needs a re-runnable check — a command that was actually run and its exit code, never a command that wasn't. A bug fix also needs a red/green pair: a red row re-runs the test at the red commit via `scripts/run_at_commit.py`, a green row shows it passing, and a code change must follow the red commit (advisory by default; `REQUIRE_RED_TEST=1` blocks).
- **Rules are enforced by code, not hope.** What can be mechanized is a hook (see `CLAUDE.md` Hooks table); convention is the residue, not the rule.

## 5. The "hard gates"

These categories always force `high-risk` and can only be lowered by a human narrowing scope:

`auth · authorization · data-loss/migration · audit/security · external provider · public
contract · weakening validation · high-blast file · workflow engine` (high-blast: e.g. `settings.json`,
any `hooks/*`, a core skill engine; workflow engine: `skills/*/SKILL.md`, skill dispatch prompts,
`agents/*.md`, `rules/*.md`).

No hook enforces these gates; the agent applies them as judgment (`rules/auto-correct-scope.md`).

A hard gate discovered *mid-task* escalates regardless of the original lane.

## 6. Pointers

| Want to… | Read |
|---|---|
| See all skills + the handoff map | `skills/README.md` |
| Understand routing / lanes in detail | `skills/feature-intake/SKILL.md`, `rules/orchestration.md` |
| Know what a hook enforces | `CLAUDE.md` → Hooks table |
| See the autonomy vs. ask-the-human rules | `rules/auto-correct-scope.md` |
