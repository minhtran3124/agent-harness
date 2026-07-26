# gh-129-durable-run-state-phase-c — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-quality-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: feature-intake
- date: 2026-07-24
- trigger: hard-gate
- question: Phase C wires the durable-run-state engine (Phases A+B, both merged) into the core workflow-engine surface itself — `skills/feature-intake/SKILL.md`, `skills/writing-plans/SKILL.md` and/or `skills/subagent-driven-development/SKILL.md`, `skills/finishing-a-development-branch/SKILL.md`, a SessionStart hook, and `scripts/harness-status.sh`. This changes what every future spec/task invocation does at each checkpoint, not just this one — do you want to proceed at high-risk with this full blast radius, or narrow the scope first?
- context: Two mechanical hard gates fire (`high-blast` for the hook, `workflow-engine` for the skill edits) plus the judgment-only "redefines the workflow itself" trigger. Confidence in the *individual* Phase C bullets is high (the issue is clear about what each checkpoint should record) — the escalation is about the blast radius and whether any scope-narrowing is wanted before touching live workflow-engine files, not about ambiguity of intent.
- options:
  - A) Proceed with full Phase C scope as specced in the issue (all four bullets: intake-init, planning/execution checkpoints, finishing checkpoint, SessionStart summary, harness-status reporting) — full chain (`/brainstorming` → `/xia2` → `/writing-plans` → `/using-git-worktrees` → `/subagent-driven-development`), with backward-compatibility as an explicit, tested design constraint (existing specs without a `RUN.json` must keep working unchanged).
  - B) Narrow scope for a first slice — e.g. only wire `feature-intake` (run-init) + `harness-status` (read-only reporting) in this pass, deferring the planning/execution/finishing checkpoint writes (the higher-blast-radius edits, since they run on every task not just at intake) to a later Phase C.2. Smaller diff, smaller review surface, but Phase C stays incomplete after this PR.
  - C) Something else — describe the scope you want.
- default_if_no_response: BLOCK
- decision: A — proceed with full Phase C scope as specced in the issue (all four bullets), full high-risk chain, backward-compatibility for existing RUN-less specs as an explicit tested design constraint.
- decided_by: Minh Tran
- decided_at: 2026-07-24
