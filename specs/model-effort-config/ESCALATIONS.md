# model-effort-config — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: orchestrator (intent-review finding #2)
- date: 2026-10-17
- trigger: ambiguous-direction
- question: Should "each agent and skill" in the intent include a consumer repo's own agents and skills, or only the harness's agents and skills?
- context: The shipped applier accepts only roles and skills in the harness defaults snapshot (design D5, SC-12): a consumer-owned agent or skill named in `harness-models.json` fails `--check` with exit 1, and consumer files are never rewritten. Intent wording "One settings file in JSON configures the model and effort for each agent and skill" admits both readings. Shipping is blocked until this is decided.
- options:
  - A) Harness agents and skills only (as built and as approved in design D5). Consumers set `model:`/`effort:` in their own frontmatter. No code change; record as advisory. A later spec can widen it.
  - B) Include consumer-owned agents and skills. The applier must accept any `.claude/agents/<name>.md` / `.claude/skills/<name>/SKILL.md`, track which lines it wrote so removal never deletes a consumer's own line, and deploy/hook must agree on the name set. Reopens D5 (`DC1`), needs new tests, and adds a task.
- default_if_no_response: BLOCK
- decision: A — harness agents and skills only (as built, design D5); recorded as advisory intent drift; a later spec can widen it
- decided_by: Minh Tran
- decided_at: 2026-10-17
