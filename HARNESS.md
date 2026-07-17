# HARNESS.md — How this repo's workflow works

This repo is a **skills framework with a risk/trust harness on top**. This file explains, in plain terms, what "the harness" is and how it shapes the way work flows.

For the full skill inventory and handoff map see [`skills/README.md`](skills/README.md).

---

## 1. Two layers: the engine and the harness

| Layer | What it is | Lives in |
|---|---|---|
| **The engine** (skills) | Invocable `/skills` that *do* the work — brainstorm, research, plan, build, review, ship. Each has hard gates and a defined handoff. | `skills/`, `agents/` |
| **The harness** (risk/trust) | A thin control layer that decides, *before* the engine runs, **how much process** a change needs and **when to involve a human**. | `skills/feature-intake/`, `hooks/`, `rules/`, `specs/<slug>/SUMMARY.md` |

The engine answers *"how do I build this?"* The harness answers *"how careful should I be, and
who needs to approve?"*

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
   hard gates, and writes `Lane:` and `confidence:` to `specs/<slug>/SUMMARY.md`.
2. **The lane picks the path:**

   | Lane | Path | Plan? | Human gate |
   |---|---|---|---|
   | **tiny** | direct `Edit` | no | none (hooks are the safety net) |
   | **normal** | `/subagent-driven-development`, two-stage review per task | yes | only if low confidence / ambiguous |
   | **high-risk** | full chain: `/brainstorming → /xia2 → /writing-plans → build` | yes | only on ambiguity or a hard gate |

3. **Confidence decides escalation.** Low confidence (any lane), or a hard gate, → stop and ask (recorded in `specs/<slug>/ESCALATIONS.md`, deny-on-no-response).
4. **Hooks corroborate the claim.** At commit time the diff is checked against the declared lane — the agent can't classify a risky change as "tiny" and slip it through.

## 4. How the harness impacts the workflow

- **Less ceremony on small work.** Typo/copy/narrow edits skip planning entirely (tiny lane).
- **More proof on risky work.** Auth, migrations, schema, public contracts, and high-blast files force `high-risk` — full plan + reviews + a recorded rollback.
- **The human is asked less, but at the right moments.** Approval is gated on *ambiguity*, not on every step. Clear work proceeds with a notice; unclear work blocks.
- **Claims must be backed by evidence.** "Done" needs a re-runnable `### Verify` artifact in `SUMMARY.md` — a row per check actually run, never a command that wasn't.
- **Rules are enforced by code, not hope.** What can be mechanized is a hook (see `CLAUDE.md` Hooks table); convention is the residue, not the rule.

## 5. The "hard gates"

These categories always force `high-risk` and can only be lowered by a human narrowing scope:

`auth · authorization · data-loss/migration · audit/security · external provider · public
contract · weakening validation · high-blast file` (e.g. `settings.json`, any `hooks/*`, a core
skill engine).

A hard gate discovered *mid-task* escalates regardless of the original lane.

## 6. Pointers

| Want to… | Read |
|---|---|
| See all skills + the handoff map | `skills/README.md` |
| Understand routing / lanes in detail | `skills/feature-intake/SKILL.md`, `rules/orchestration.md` |
| Know what a hook enforces | `CLAUDE.md` → Hooks table |
| See the autonomy vs. ask-the-human rules | `rules/auto-correct-scope.md` |
