# gh-121-spec-ticket-prefix — Escalations

Default: **deny-on-no-response**. No recorded decision → work stays blocked.
(Enforced: `hooks/commit-quality-gate.sh` denies commits touching this slug while any `decision:` is `pending`.)

---

## E001

- raised_by: orchestrator (feature-intake)
- date: 2026-07-20
- trigger: hard-gate
- question: Confirm high-risk execution — the change edits five wired `hooks/*` scripts plus core gate scripts (high-blast-radius files per Rule 4); proceed through the full high-risk chain (brainstorming → xia2 → writing-plans → worktree → subagent-driven-development)?
- context: All implementation for issue #121 is blocked on this confirmation.
- options:
  - A) Confirm high-risk, proceed with the full chain — hooks/scripts are verified by `bash scripts/run-tests.sh` at every step.
  - B) Narrow scope (e.g. docs/skills convention only, defer hook/script changes) — lowers blast radius but leaves the convention unenforced.
- default_if_no_response: BLOCK
- decision: A — high-risk confirmed; proceed with the full chain, `bash scripts/run-tests.sh` at every hook/script step
- decided_by: Minh Tran (interactive, AskUserQuestion)
- decided_at: 2026-07-20

## E002

- raised_by: orchestrator (feature-intake)
- date: 2026-07-20
- trigger: ambiguous-direction
- question: Settle the two open design questions the issue explicitly defers: (1) prefix vocabulary + ticket-less fallback (`adhoc-<slug>` vs plain `<slug>`), (2) migrate existing spec folders vs grandfather them?
- context: Brainstorming/design cannot conclude without these; the issue proposes `gh-` / `lin-` and says "grandfathering is likely fine" but marks both as to-be-decided.
- options:
  - A) Accept the issue's proposed defaults — `gh-<issue#>-<slug>`, `lin-<TEAM-###>-<slug>`, plain `<slug>` for ticket-less work, grandfather existing folders (verify gates parse `specs/<anything>/`).
  - B) Same prefixes but `adhoc-<slug>` for ticket-less work — explicit at the cost of noisier names.
  - C) Decide during brainstorming with the human in the loop.
- default_if_no_response: BLOCK
- decision: A — issue defaults: `gh-<issue#>-<slug>` / `lin-<TEAM-###>-<slug>`, plain `<slug>` for ticket-less work, grandfather existing folders (verify gates parse `specs/<anything>/`)
- decided_by: Minh Tran (interactive, AskUserQuestion)
- decided_at: 2026-07-20
