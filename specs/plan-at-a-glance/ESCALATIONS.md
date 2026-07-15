# plan-at-a-glance — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.

---

## E001

- raised_by: orchestrator (feature-intake)
- date: 2026-07-15
- trigger: hard-gate + ambiguous-direction
- question: Which of the four proposed directions (A/B/C/D) should ship, and may I modify the core skill engine `render_plan.py` (and the `render-plan-on-write.sh` hook) to do it?
- context: Issue #54 is explicitly framed "for discussion, not a committed design." High-risk lane is forced by editing `render_plan.py` (a named high-blast core skill engine). Scope must be narrowed by a human before the full high-risk chain runs.
- options:
  - A) Scope to the issue's **suggested first step: (A) + (B) only** — emit a derived, additive "At a glance" block (wave×task table + Mermaid + counts) plus in-place checkbox progress, written back into tracked `PLAN.md` by `render_plan.py`. Defer C and D. (Recommended — lowest cost, highest value, ships the readable view everywhere for free.)
  - B) Do (A)+(B)+(D) — also add a single `build_roadmap.py` entry point for the cross-plan overview.
  - C) Full scope A+B+C+D — including publishing `PLAN.html` as a shareable Artifact URL (adds an external-systems surface).
  - D) A only — self-summarizing block, no progress checkboxes yet.
- default_if_no_response: BLOCK
- decision: **A** — ship (A)+(B) only (derived additive "At a glance" block: wave×task table + Mermaid + counts, plus in-place checkbox progress, written into tracked PLAN.md by render_plan.py). Defer C and D. Editing the `render_plan.py` core skill engine (and the `render-plan-on-write.sh` hook if needed) is authorized within this scope. Lane stays **high-risk** (scope narrowed, not downgraded).
- decided_by: Minh Tran (minhtran3124)
- decided_at: 2026-07-15
