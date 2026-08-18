# Research: Comparing `superpowers` with our `brainstorming` skill

> Date: 2026-06-15
> Source: `obra/superpowers` (GitHub, main branch) — the `skills/brainstorming/SKILL.md` skill and the plugin README
> Scope: Side-by-side analysis to extract lessons for `skills/brainstorming/SKILL.md`
> Method: Content retrieved via WebFetch (summarized by a small model, not 100% raw) and then compared against the skill currently in the repo. Some wording nuances may be lost; the structural conclusions were verified by text matching.

---

## 0. The most important finding: this is a BLOODLINE relationship, not a rivalry

Unlike `ce-brainstorm` (a parallel product with new techniques to borrow), **`superpowers` is the ANCESTOR of the brainstorming skill — and of nearly the entire workflow — in this repo.** Evidence: identically named skills appear on both sides:

`brainstorming`, `writing-plans`, `executing-plans`, `subagent-driven-development`, `using-git-worktrees`, `finishing-a-development-branch`, `systematic-debugging`, `requesting-code-review`, `verification-before-completion`.

For the `brainstorming` skill specifically: our version is **almost identical** to superpowers, and we have deliberately **upgraded** it in a few places. In other words: we are not "learning something new" from superpowers brainstorming — we already are a **superset** of it. What is worth doing is (a) confirming the lineage so we know what to sync with upstream, and (b) picking up a few small things we skipped when forking.

Sophistication ranking of the 3 brainstorm skills: **ce-brainstorm (highest) > ours (superpowers + subagent review + xia2 + lane) > superpowers brainstorming (original/baseline).**

---

## 1. What `superpowers` is

A plugin that packages an entire **software development methodology**, not a scattering of coding tips. Core philosophy (per the README):

1. **Test-Driven Development** — tests always come before code.
2. **Systematic over ad-hoc** — process beats guesswork.
3. **Complexity reduction** — simplicity is the top-priority goal.
4. **Evidence over claims** — verify before declaring success.

Distinctive point: it **"steps back and asks what you are actually trying to do"** before designing, and it **mandates** a sequential pipeline (not an optional suggestion):

> brainstorming → design validation → planning → subagent-driven development → testing → code review → branch completion

Its `subagent-driven-development` skill dispatches a fresh agent for each task with **two-tier review** (spec compliance → code quality) — this is exactly the model our `rules/orchestration.md` and `wave-parallelism.md` use.

---

## 2. The `brainstorming` skill: what is IDENTICAL (we inherited it)

- The **9-step** process (explore context → offer visual companion → ask Qs → 2-3 approaches → present design → write doc → review → user review → writing-plans).
- **HARD-GATE** with identical wording: *"Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it."*
- The **"This Is Too Simple To Need A Design"** anti-pattern — identical.
- Identical **Key Principles**: one-question-at-a-time, multiple-choice preferred, YAGNI ruthlessly, explore alternatives, incremental validation, be flexible.
- **Visual companion** (browser mockup).
- Step 4: **lead with the recommended approach** (same as us — and this is exactly the point where `ce-brainstorm` does the opposite = present-then-recommend; see the ce-brainstorm doc).
- Design split into sections by complexity, reviewed section by section.
- Terminal state = `writing-plans`.

---

## 3. What we HAVE CHANGED relative to the original superpowers

| Aspect | superpowers (original) | ours (modified) | Assessment |
|---|---|---|---|
| Step 6 — doc path | `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md` (flat, by date) | `specs/<slug>/design.md` (by slug directory, tracked in git) | Ours fits the per-slug spec→plan→implement structure |
| Step 7 — spec review | **Self-review** (self-scan: placeholder/TBD, internal contradictions, correct scope, ambiguity) | **`spec-document-reviewer` subagent loop** (independent, up to 5 rounds) | **We upgraded it** — independent review > self-review |
| Existing-code research step | Absent (goes straight from brainstorm → writing-plans) | Inserts **`xia2`** before writing-plans | We added a "discover what already exists" step |
| Reading past decisions | Absent | Reads the `docs/solutions/` decision track (avoids re-proposing a rejected approach) | We added it |
| Risk classification | Absent | Integrates `feature-intake` (lane tiny/normal/high-risk) | We added it (though the brainstorming skill does not yet exploit it — see the ce-brainstorm doc) |

---

## 4. So what CAN we still learn from superpowers?

Since we are already a superset, there is less to learn than from ce-brainstorm — but it is real:

### 1. The step-7 self-review as an "always-on, low-cost" gate
This is the most valuable borrowable point. Our `spec-document-reviewer` subagent loop is **strong but heavy** — overkill for small work (tiny/Lightweight). The superpowers self-review checklist (scan for TBD/placeholder, internal consistency, correct scope, ambiguity removal) is a **light, always-running** gate.

→ **Combine with the lane-awareness recommendation** from the `ce-brainstorm` doc: use the **superpowers self-review as the light tier** (for tiny/Lightweight) and **keep the subagent loop for normal/high-risk**. That is, superpowers gives us exactly the "cheap-tier review mechanism" that the ceremony-scaling piece needs.

### 2. Lineage awareness & syncing with upstream
Since 9 of our skills are forked from superpowers, every time upstream changes the HARD-GATE, the Key Principles, or the brainstorm process, we should know about it so we can decide whether to sync or deliberately diverge. We should state explicitly: "this is a fork of superpowers; the intentional divergence points are: subagent review, xia2, lane, docs/solutions, specs/<slug>".

### 3. The philosophy confirms our direction
The four core superpowers principles (TDD, systematic-over-ad-hoc, complexity-reduction, evidence-over-claims) are already present in `rules/behavior.md` and `rules/orchestration.md` (the "evidence over assertion" section). Nothing new to add — just confirmation that we are on the right track.

### 4. Meta-skills worth referencing (beyond brainstorming)
- `writing-skills` — a skill for writing skills (we currently reference `/skill-creator` externally).
- `dispatching-parallel-agents` — the agent fan-out model (we already have it in orchestration/wave-parallelism).
Not directly about brainstorming, but a useful reference when tuning the system.

---

## 5. Cross-comparison: superpowers vs ce-brainstorm (for brainstorming)

| Technique | superpowers | ours | ce-brainstorm |
|---|---|---|---|
| Ceremony scaling by scope | ❌ (fixed) | ⚠️ (has lane, but the skill does not use it) | ✅ (Lightweight/Standard/Deep) |
| Product Pressure Test (gap lenses) | ❌ | ❌ | ✅ |
| Synthesis checkpoint before writing | ❌ | ❌ | ✅ |
| Anti-anchoring (present-then-recommend) | ❌ (leads with the recommendation) | ❌ (leads with the recommendation) | ✅ |
| Spec review | Self-review (light) | Subagent loop (heavy, independent) ✅ | Separate ce-doc-review skill |
| Interactive visual companion | ✅ | ✅ | ❌ (static diagrams only) |
| Existing-code discovery before plan | ❌ | ✅ (xia2) | ⚠️ (Phase 1.1 scan) |
| Brainstorm resume detection | ❌ | ❌ | ✅ |

---

## 6. Consolidated recommendations (merging both research efforts)

1. **Make brainstorming lane-aware** + **use the superpowers self-review for the light tier**, keeping the subagent loop for normal/high-risk. (Resolves the conflict with `orchestration.md` while taking advantage of the cheap superpowers mechanism.)
2. **Add the Product Pressure Test** (5 gap lenses) — learned from ce-brainstorm; highest novelty.
3. **Add a synthesis/scope-confirmation checkpoint** before writing `design.md` — learned from ce-brainstorm.
4. **Decide the anchoring question** (present-then-recommend vs lead-with-recommendation) — superpowers AND we both lead with the recommendation; ce-brainstorm argues against this. Needs a human decision.
5. **Lineage note**: clearly mark the skill as a fork of superpowers + list the intentional divergence points, for future upstream syncing.

All of these touch the core skill (`skills/brainstorming/SKILL.md`) — a higher-risk class of edit under our rules, so we stop at the analysis level.
