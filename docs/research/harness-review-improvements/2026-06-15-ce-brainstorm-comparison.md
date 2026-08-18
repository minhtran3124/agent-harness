# Research: Comparing `ce-brainstorm` with our `brainstorming` skill

> Date: 2026-06-15
> Source: `everyinc/compound-engineering-plugin` — skill `compound-engineering:ce-brainstorm` (v3.12.0)
> Scope: Side-by-side analysis to draw out improvement lessons for `skills/brainstorming/SKILL.md`
> Read: `ce-brainstorm/SKILL.md` + `references/synthesis-summary.md` + `references/brainstorm-sections.md`; and this repo's `skills/brainstorming/SKILL.md`.

---

## 1. What `ce-brainstorm` is

A skill that answers the **WHAT** question — what to build — not **HOW**. It runs before `/ce-plan` (the skill that handles the HOW). Its durable output is a **right-sized requirements doc**, and its core characteristic: **ceremony scales with the size of the work**, rather than being fixed.

Phase structure:

- **Phase 0** — determine the output format, detect/resume an earlier brainstorm, classify the domain (software / non-software / no brainstorm needed), decide *whether a brainstorm is needed at all*, and classify size into **Lightweight / Standard / Deep**, with Deep further split into **feature-vs-product**.
- **Phase 1.2 Product Pressure Test** — an internal scan (the agent analyzes on its own) through "gap lenses": evidence / specificity / counterfactual / attachment / durability; only gaps that genuinely exist get raised as questions.
- **Phase 1.3** — dialogue driven by open-ended "rigor probes" plus an **integration check** before exiting the phase ("stitch together what the user has said, surface non-obvious consequences").
- **Phase 2** — propose approaches using a deliberately non-obvious angle (inversion / constraint removal / analogy), present all options first and only then recommend, optionally adding a higher-upside "challenge" option; detail is capped at the *mechanism* level and never reaches architecture.
- **Phase 2.5 Synthesis Summary** — a scope-confirmation checkpoint *before* writing the doc (two tiers: an internal 3-bucket draft → a compressed conversational synthesis), with a Path A/B gate, "keep-tests", per-tier bullet budgets, a soft-cut mechanism when it loops, and re-present-after-revision discipline.
- **Phase 3** — write the doc *only when it's worth writing*, following a rich section catalog with prose-economy rules.

---

## 2. Architecture comparison table

| Aspect | `brainstorming` (ours) | `ce-brainstorm` |
|---|---|---|
| Ceremony | **Fixed** — "every project, no exceptions", always the full checklist + HARD-GATE | **Elastic** — skipped when things are already clear, with Lightweight/Standard/Deep tiers |
| Always write a doc? | Yes (`design.md` always) | No — there's a "is this doc worth writing?" gate |
| Rigor-check phase before proposing | None | **Product Pressure Test** (5 gap lenses) |
| Option generation | "propose 2-3 directions" | + a mandatory non-obvious angle + a challenge option |
| Recommendation order | **Lead with the recommendation** | **Present everything, then recommend** (anti-anchoring) |
| Scope checkpoint | None (jumps straight from design → writing) | **Phase 2.5 synthesis** + revision loop |
| Question discipline | "prefer multiple choice, open-ended is fine too" | Explicit rules + a test for when an open-ended question is warranted |
| Independent review | Has a spec-document-reviewer subagent loop ✅ | (split out into a separate `ce-doc-review` skill) |
| Visual support | Interactive browser companion ✅ | Static diagrams/HTML inside the doc |
| Resume detection | None | Phase 0.1 ✅ |
| WHAT/HOW separation | Blurred — design covers "architecture, components, data flow, error handling, testing" | Clear — mechanism level only; architecture → ce-plan |

---

## 3. What's worth learning (in priority order)

### 1. Right-size the ceremony — and fix an internal contradiction we have
This is the biggest one. Our skill mandates the full chain for "a todo list, a one-function util, a config change — all of them." But our own `rules/orchestration.md` says the opposite: `design.md` is signal-triggered ("only on a real design fork (≥2 viable approaches) or high-risk"), and `feature-intake` routes the **tiny** lane straight to direct edits. Which means the brainstorming skill currently **contradicts our own lane system**. `ce-brainstorm` independently confirms that the elastic direction is the right one.

**Recommendation:** make brainstorming lane-aware — Lightweight/tiny needs only a brief alignment and can skip `design.md`; HARD-GATE and the review loop apply only to normal/high-risk.

### 2. Product Pressure Test (the gap lenses)
Genuinely novel and high value — we have nothing like it. The evidence / specificity / counterfactual / attachment / durability lenses turn brainstorming from *requirements extraction* into *product interrogation*, and framing it as "the agent analyzes internally, raises only real gaps" avoids the checkbox-theater failure mode. This is the easiest idea to graft in.

Summary of the 5 lenses:
- **Evidence gap** — a need/desire is asserted but nothing shows what the user has actually done about it (time spent, money paid, workarounds built). → Ask for the most concrete thing someone has done about this.
- **Specificity gap** — the beneficiary is described so abstractly that the agent has to invent who they are. → Require naming a specific person or narrow segment and what changes for them.
- **Counterfactual gap** — it isn't clear what the user does today when they hit the problem, and what changes if nothing ships. → Ask about the current workaround and what it costs.
- **Attachment gap** — a specific solution shape is treated as "the thing being built", rather than the value that shape is supposed to deliver. → Ask what the smallest version that still delivers real value looks like.
- **Durability gap** (Deep-product only) — the value rests on a state of the world that could shift. → Ask how the idea holds up against the most plausible near-term changes.

### 3. A synthesis checkpoint before writing (Phase 2.5)
We jump straight from "design approved" to "write design.md". `ce-brainstorm` inserts a scope-confirmation step with the insight: *"the user agreed to each thing individually in dialogue but never saw the whole picture."* The two-tier shape (full internal draft → compressed conversational checkpoint) plus revise-before-writing discipline is a meaningful quality gate, and cheaper than our subagent review loop because it sits inline.

### 4. Anti-anchoring on options — a direct contradiction to resolve
Our skill says *"Lead with the recommended option."* `ce-brainstorm` says *present all options first, then recommend,* because leading with a recommendation anchors the user early. Their reasoning is sound; this should be flagged as a decision to make deliberately, not to keep our way by default.

### 5. Sharper question discipline + an integration check
Their Interaction Rule 5 (an explicit test for when a question should be open-ended rather than a menu — *"if you have to strain to fill in the choice slots, then it's an open-ended question"*) and the fact that rigor probes are *deliberately* left open (so the menu doesn't tip the user off about what counts as a good answer) are both sharp. Beyond that, the pre-exit integration check has no equivalent on our side.

### 6. A cleaner WHAT/HOW boundary
Our design covers "architecture, components, data flow, error handling, testing" — pulling HOW into the brainstorm. Since our workflow already has `xia2 → writing-plans` downstream, the design doc could stay at the mechanism/behavior level and leave architecture to the plans. (Note: consumers of `design.md` may currently expect that level of detail — check before changing.)

**Lower priority:** resume detection (Phase 0.1), the prose-economy-style section catalog in `brainstorm-sections.md`, and the "stress test" for deciding whether a doc is worth writing.

---

## 4. What we do better (keep these)

- **Built-in independent review** — our spec-document-reviewer subagent loop is structured adversarial review right inside the skill; `ce-brainstorm` pushes that out into a separate `ce-doc-review` skill.
- **Interactive visual companion** — browser mockups beat static diagrams for layout/wireframe questions.
- **Lane/hard-gate integration** — HARD-GATE plus reading the decision track in `docs/solutions/` (not re-proposing already-rejected options) ties brainstorming into the broader governance system.

---

## 5. Concrete proposed changes (in priority order)

1. **Make brainstorming lane-aware** (resolves the internal contradiction with `orchestration.md`) — *high value, and simultaneously a correctness fix.*
2. **Add a Product Pressure Test phase** before proposing options — *highest novelty.*
3. **Add a synthesis/scope-confirmation checkpoint** before writing `design.md`.
4. **Decide the anchoring question** (lead-with-recommendation vs present-then-recommend) — needs a human decision.
5. **Tighten question discipline** + add an integration check.

All of these are changes to a core skill (`skills/brainstorming/SKILL.md`) — exactly the kind of edit our rules treat as higher risk, so this stopped at analysis rather than editing the file.
